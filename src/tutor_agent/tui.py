"""The tutor pane (ADR 0009, 0028). Only `tutor tui` imports this module: Textual is a heavy import.

Left: the concept list, grouped by status. Right: the highlighted concept's cached lesson, or a
short card. Enter opens a lesson (marks it `seen`, generates it on first open). Under it, an
input for follow-up questions (ADR 0012, 0029); the thread lives per concept while the pane is
open. `w` picks a recent session and explains its latest turn ("what just happened", F8).
Every model call runs in a worker thread, so the pane never freezes. The concept memory is
polled once a second, so concepts the detector adds show up without a restart.
"""

from __future__ import annotations

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Markdown, OptionList
from textual.widgets.option_list import Option

from tutor_agent import explain, followups, lessons, paths, settings
from tutor_agent.log import get_logger
from tutor_agent.store import Concept, ConceptStore, Status, StoreError

GROUPS = (Status.NEW, Status.SEEN, Status.UNDERSTOOD, Status.DISMISSED)

# Which status keys apply to which current status (learner model, ADR 0018).
TRANSITIONS: dict[Status, set[Status]] = {
    Status.UNDERSTOOD: {Status.NEW, Status.SEEN},
    Status.SEEN: {Status.UNDERSTOOD},
    Status.DISMISSED: {Status.NEW, Status.SEEN, Status.UNDERSTOOD},
    Status.NEW: {Status.DISMISSED},  # undo a dismissal
}


def project_name(concept: Concept) -> str:
    project = concept.sources[-1].project if concept.sources else None
    return project.rstrip("/").rsplit("/", 1)[-1] if project else "?"


def ordered(concepts: list[Concept], show_dismissed: bool) -> list[tuple[Status, list[Concept]]]:
    """Concepts grouped by status (`new` first), newest first inside a group."""
    out = []
    for status in GROUPS:
        if status is Status.DISMISSED and not show_dismissed:
            continue
        group = sorted((c for c in concepts if c.status is status), key=lambda c: c.created_at, reverse=True)
        if group:
            out.append((status, group))
    return out


def card(concept: Concept) -> str:
    source = concept.sources[-1] if concept.sources else None
    lines = [
        f"# {concept.name}",
        "",
        f"*{concept.category}* · **{concept.status}** · {project_name(concept)} · "
        f"seen {len(concept.sources)}×",
        "",
        concept.summary,
    ]
    if source:
        lines += ["", f"> {source.context}"]
    lines += ["", "Press **Enter** to open the lesson."]
    return "\n".join(lines)


def thread_markdown(thread: list[followups.Turn], pending: str | None) -> str:
    if not thread and pending is None:
        return ""
    parts = ["", "---", "", "## Follow-ups"]
    for t in thread:
        parts += ["", f"**You:** {t.question}", "", t.answer]
    if pending is not None:
        parts += ["", f"**You:** {pending}", "", "*Thinking…*"]
    return "\n".join(parts)


class SessionPicker(ModalScreen[explain.Session | None]):
    """Pick one of the recently active sessions. Enter picks, Escape cancels."""

    CSS = """
    SessionPicker { align: center middle; }
    #sessions { width: 90; max-height: 24; border: round $primary; }
    """
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, sessions: list[explain.Session]) -> None:
        super().__init__()
        self.sessions = sessions

    def compose(self) -> ComposeResult:
        ol = OptionList(*(Option(s.label(), id=str(i)) for i, s in enumerate(self.sessions)), id="sessions")
        ol.border_title = "What just happened in…"
        yield ol

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        self.dismiss(self.sessions[int(event.option_id)])

    def action_cancel(self) -> None:
        self.dismiss(None)


class TutorApp(App):
    TITLE = "Tutor"
    CSS = """
    #concepts { width: 42; border-right: solid $primary-background; }
    #lesson-pane { padding: 0 2; }
    #ask { dock: bottom; }
    """
    BINDINGS = [
        Binding("u", "set_status('understood')", "Understood"),
        Binding("s", "set_status('seen')", "Back to seen"),
        Binding("d", "set_status('dismissed')", "Dismiss"),
        Binding("n", "set_status('new')", "Undo dismiss"),
        Binding("r", "regenerate", "Regenerate"),
        Binding("h", "toggle_dismissed", "Show dismissed"),
        Binding("f", "ask", "Follow-up"),
        Binding("w", "what_happened", "What just happened"),
        Binding("x", "show_explanation", "Last explanation"),
        Binding("escape", "focus_list", "Back to list", show=False),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, store: ConceptStore | None = None, cache: lessons.LessonCache | None = None,
                 cfg: settings.Settings | None = None, poll_s: float = 1.0) -> None:
        super().__init__()
        self.store = store or ConceptStore()
        self.cache = cache or lessons.LessonCache()
        self.cfg = cfg or settings.load()
        self.poll_s = poll_s
        self.show_dismissed = False
        self.concepts: dict[str, Concept] = {}
        self.generating: set[str] = set()
        self.errors: dict[str, str] = {}  # last failed generation per concept, shown until retried
        self.threads: dict[str, list[followups.Turn]] = {}  # follow-ups per concept, kept while open
        self.asking: dict[str, str] = {}  # concept id -> the question being answered
        self.explaining: explain.Session | None = None
        self.explanation: tuple[explain.Session, str] | None = None  # the last one, for `x`
        self.showing_explanation = False  # the right side shows an explanation, not a concept
        self._highlighted: str | None = None
        self._stamp: tuple[int, int] | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            self.concept_list = OptionList(id="concepts")
            yield self.concept_list
            with Vertical():
                # Kept as attributes: `query_one` searches the active screen, which is the session
                # picker while it is open.
                with VerticalScroll(id="lesson-pane") as self.lesson_pane:
                    self.lesson_md = Markdown(id="lesson")
                    yield self.lesson_md
                self.ask_input = Input(placeholder="f: ask a follow-up about the open lesson · Esc: back", id="ask")
                yield self.ask_input
        yield Footer()

    def on_mount(self) -> None:
        self.reload()
        self.set_interval(self.poll_s, self.poll_store)
        self.concept_list.focus()

    # --- concept list -------------------------------------------------------------------------

    def _file_stamp(self) -> tuple[int, int] | None:
        try:
            st = self.store.path.stat()
        except FileNotFoundError:
            return None
        return (st.st_mtime_ns, st.st_size)

    def poll_store(self) -> None:
        if self._file_stamp() != self._stamp:
            self.reload()

    def reload(self) -> None:
        """Read the concept memory and rebuild the list, keeping the highlighted concept."""
        self._stamp = self._file_stamp()
        try:
            self.concepts = {c.id: c for c in self.store.list()}
        except StoreError as e:
            get_logger().error("tutor pane: %s", e)
            self.show_markdown(f"# Concept memory unreadable\n\n{e}")
            return
        option_list = self.concept_list
        keep = self.highlighted_id()
        option_list.clear_options()
        for status, group in ordered(list(self.concepts.values()), self.show_dismissed):
            option_list.add_option(Option(Text(f"{status.upper()} ({len(group)})", style="bold"), disabled=True))
            for c in group:
                label = Text(c.name)
                label.append(f"\n  {c.category} · {project_name(c)}", style="dim")
                option_list.add_option(Option(label, id=c.id))
        self.sub_title = f"{sum(c.status is Status.NEW for c in self.concepts.values())} new"
        if not self.concepts:
            self.show_markdown("# No concepts yet\n\nThey appear here as the detector finds them.")
            return
        self.highlight(keep)

    def highlight(self, cid: str | None) -> None:
        option_list = self.concept_list
        index = None
        if cid is not None:
            try:
                index = option_list.get_option_index(cid)
            except Exception:  # hidden now (dismissed) or gone
                index = None
        if index is None:
            index = next((i for i in range(option_list.option_count)
                          if not option_list.get_option_at_index(i).disabled), None)
        if index is not None:
            option_list.highlighted = index
        self.show_current()

    def highlighted_id(self) -> str | None:
        option_list = self.concept_list
        if option_list.highlighted is None:
            return None
        return option_list.get_option_at_index(option_list.highlighted).id

    def current(self) -> Concept | None:
        cid = self.highlighted_id()
        return self.concepts.get(cid) if cid else None

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option_list is not self.concept_list:
            return  # the session picker's list
        # A reload clears and refills the list, which posts highlight events for options that are
        # no longer highlighted by the time they arrive. Only a real move leaves an explanation.
        if event.option_id != self.highlighted_id():
            return
        if event.option_id != self._highlighted:
            self._highlighted = event.option_id
            self.showing_explanation = False
        self.show_current()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list is self.concept_list and event.option_id:
            self.showing_explanation = False
            self.open(event.option_id)

    # --- lesson pane --------------------------------------------------------------------------

    def show_markdown(self, text: str, loading: bool = False, scroll_end: bool = False) -> None:
        md = self.lesson_md
        md.loading = loading
        md.update(text)
        pane = self.lesson_pane
        if scroll_end:
            pane.call_after_refresh(pane.scroll_end, animate=False)
        else:
            pane.scroll_home(animate=False)

    def show_current(self, scroll_end: bool = False) -> None:
        """Cached lesson if there is one (no LLM call), a generating state, an error, or the card."""
        if self.showing_explanation:
            return
        concept = self.current()
        if concept is None:
            return
        if concept.id in self.generating:
            self.show_markdown(f"# {concept.name}\n\nGenerating the lesson…", loading=True)
            return
        lesson = self.cache.get(concept.id)
        if lesson is not None:
            thread = thread_markdown(self.threads.get(concept.id, []), self.asking.get(concept.id))
            self.show_markdown(f"# {concept.name}\n\n{lesson.text}{thread}", scroll_end=scroll_end)
        elif concept.id in self.errors:
            self.show_markdown(f"{card(concept)}\n\n**Lesson failed:** {self.errors[concept.id]}")
        else:
            self.show_markdown(card(concept))

    def open(self, cid: str) -> None:
        """Open a lesson: `new` becomes `seen`, and the lesson is generated if not cached."""
        concept = self.concepts.get(cid)
        if concept is None:
            return
        if concept.status is Status.NEW:
            self._change(lambda: self.store.mark_seen(cid))
        if not self.cache.has(cid):
            self.start_generation(cid)
        self.show_current()

    def action_regenerate(self) -> None:
        concept = self.current()
        if concept is not None:
            self.start_generation(concept.id)
            self.show_current()

    def start_generation(self, cid: str) -> None:
        if cid in self.generating:
            return
        self.generating.add(cid)
        self.errors.pop(cid, None)
        self.generate_lesson(self.concepts[cid])

    @work(thread=True, group="lessons")
    def generate_lesson(self, concept: Concept) -> None:
        try:
            lesson = lessons.generate(concept, self.cfg)
            self.cache.put(lesson)
            error = None
        except Exception as e:  # ClaudeError, LessonError, OSError: shown in the pane, logged
            get_logger().exception("lesson failed for %s", concept.id)
            error = str(e) or type(e).__name__
        self.call_from_thread(self.lesson_done, concept.id, error)

    def lesson_done(self, cid: str, error: str | None) -> None:
        self.generating.discard(cid)
        if error:
            self.errors[cid] = error
        if self.highlighted_id() == cid:
            self.show_current()

    # --- follow-ups (ADR 0012, 0029) -----------------------------------------------------------

    def action_ask(self) -> None:
        self.ask_input.focus()

    def action_focus_list(self) -> None:
        self.concept_list.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        question = event.value.strip()
        if not question:
            return
        concept = self.current()
        lesson = self.cache.get(concept.id) if concept else None
        if self.showing_explanation or concept is None or lesson is None:
            self.notify("Open a lesson first (Enter), then ask about it.", severity="warning")
            return
        if concept.id in self.asking:
            self.notify("Still answering the last question.", severity="warning")
            return
        event.input.clear()
        self.asking[concept.id] = question
        known = followups.known_concepts(list(self.concepts.values()), exclude=concept.id)
        self.answer_followup(concept, lesson, list(self.threads.get(concept.id, [])), known, question)
        self.show_current(scroll_end=True)

    @work(thread=True, group="followups")
    def answer_followup(self, concept: Concept, lesson: lessons.Lesson, thread: list[followups.Turn],
                        known: list[Concept], question: str) -> None:
        try:
            text, error = followups.answer(concept, lesson, thread, known, question, self.cfg), None
        except Exception as e:  # ClaudeError, FollowUpError: shown as a notification, logged
            get_logger().exception("follow-up failed for %s", concept.id)
            text, error = None, str(e) or type(e).__name__
        self.call_from_thread(self.followup_done, concept.id, question, text, error)

    def followup_done(self, cid: str, question: str, text: str | None, error: str | None) -> None:
        self.asking.pop(cid, None)
        if error:
            self.notify(f"Follow-up failed: {error}", severity="error")
            if not self.ask_input.value:
                self.ask_input.value = question  # don't make me type it again
        else:
            self.threads.setdefault(cid, []).append(followups.Turn(question, text))
        if self.highlighted_id() == cid:
            self.show_current(scroll_end=True)

    # --- what just happened (F8, ADR 0029) -----------------------------------------------------

    def action_what_happened(self) -> None:
        if self.explaining is not None:
            self.notify("Still explaining the last turn.", severity="warning")
            return
        try:
            sessions = explain.recent_sessions()
        except OSError as e:
            self.notify(f"Can't list sessions: {e}", severity="error")
            return
        if not sessions:
            self.notify(f"No sessions found in {paths.claude_projects_dir()}.", severity="warning")
            return
        self.push_screen(SessionPicker(sessions), self.start_explanation)

    def start_explanation(self, session: explain.Session | None) -> None:
        if session is None:
            return
        self.explaining = session
        self.showing_explanation = True
        self.show_markdown(f"# What just happened\n\n{session.label()}\n\nReading the latest turn…", loading=True)
        self.explain_turn(session, followups.known_concepts(list(self.concepts.values())))

    @work(thread=True, group="explain")
    def explain_turn(self, session: explain.Session, known: list[Concept]) -> None:
        try:
            turn = explain.latest_turn(session)
            text, error = explain.explain(turn, known, self.cfg), None
            if turn.dropped_events:
                text += f"\n\n*{turn.dropped_events} earlier events of this long turn were left out.*"
        except Exception as e:  # OSError, ClaudeError, ExplainError
            get_logger().exception("explanation failed for %s", session.transcript)
            text, error = None, str(e) or type(e).__name__
        self.call_from_thread(self.explanation_done, session, text, error)

    def explanation_done(self, session: explain.Session, text: str | None, error: str | None) -> None:
        self.explaining = None
        if error:
            self.notify(f"Explanation failed: {error}", severity="error")
            if self.showing_explanation:
                self.showing_explanation = False
                self.show_current()
            return
        self.explanation = (session, text)
        if self.showing_explanation:
            self.action_show_explanation()
        else:
            self.notify("Explanation ready: press x to show it.")

    def action_show_explanation(self) -> None:
        if self.explaining is not None and self.explanation is None:
            self.showing_explanation = True
            self.show_markdown("# What just happened\n\nReading the latest turn…", loading=True)
            return
        if self.explanation is None:
            self.notify("No explanation yet: press w to pick a session.", severity="warning")
            return
        session, text = self.explanation
        self.showing_explanation = True
        project = session.project or "unknown project"
        self.show_markdown(f"# What just happened\n\n*{project} · session {session.session_id[:8]}*\n\n{text}")

    # --- status actions -----------------------------------------------------------------------

    def action_set_status(self, status: str) -> None:
        target = Status(status)
        concept = self.current()
        if concept is None:
            return
        if concept.status not in TRANSITIONS[target]:
            self.notify(f"Can't go from {concept.status} to {target}.", severity="warning")
            return
        self._change(lambda: self.store.set_status(concept.id, target))
        self.notify(f"{concept.name}: {target}")

    def action_toggle_dismissed(self) -> None:
        self.show_dismissed = not self.show_dismissed
        self.reload()

    def _change(self, write) -> None:
        try:
            write()
        except (StoreError, KeyError, OSError) as e:
            get_logger().error("tutor pane: status change failed: %s", e)
            self.notify(f"Not saved: {e}", severity="error")
        self.reload()


def main() -> int:
    try:
        cfg = settings.load()
    except settings.SettingsError as e:
        print(f"tutor: {e}")
        return 1
    TutorApp(cfg=cfg).run()
    return 0
