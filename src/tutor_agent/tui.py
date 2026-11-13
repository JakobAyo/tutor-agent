"""The tutor pane (ADR 0009, 0028). Only `tutor tui` imports this module: Textual is a heavy import.

Left: the concept list, grouped by status. Right: the highlighted concept's cached lesson, or a
short card. Enter opens a lesson (marks it `seen`, generates it on first open). Lessons are
generated in a worker thread, so the pane never freezes. The concept memory is polled once a
second, so concepts the detector adds show up without a restart.
"""

from __future__ import annotations

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, Markdown, OptionList
from textual.widgets.option_list import Option

from tutor_agent import lessons, settings
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


class TutorApp(App):
    TITLE = "Tutor"
    CSS = """
    #concepts { width: 42; border-right: solid $primary-background; }
    #lesson-pane { padding: 0 2; }
    """
    BINDINGS = [
        Binding("u", "set_status('understood')", "Understood"),
        Binding("s", "set_status('seen')", "Back to seen"),
        Binding("d", "set_status('dismissed')", "Dismiss"),
        Binding("n", "set_status('new')", "Undo dismiss"),
        Binding("r", "regenerate", "Regenerate"),
        Binding("h", "toggle_dismissed", "Show dismissed"),
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
        self._stamp: tuple[int, int] | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield OptionList(id="concepts")
            with VerticalScroll(id="lesson-pane"):
                yield Markdown(id="lesson")
        yield Footer()

    def on_mount(self) -> None:
        self.reload()
        self.set_interval(self.poll_s, self.poll_store)
        self.query_one(OptionList).focus()

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
        option_list = self.query_one(OptionList)
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
        option_list = self.query_one(OptionList)
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
        option_list = self.query_one(OptionList)
        if option_list.highlighted is None:
            return None
        return option_list.get_option_at_index(option_list.highlighted).id

    def current(self) -> Concept | None:
        cid = self.highlighted_id()
        return self.concepts.get(cid) if cid else None

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        self.show_current()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_id:
            self.open(event.option_id)

    # --- lesson pane --------------------------------------------------------------------------

    def show_markdown(self, text: str, loading: bool = False) -> None:
        md = self.query_one(Markdown)
        md.loading = loading
        md.update(text)
        self.query_one("#lesson-pane").scroll_home(animate=False)

    def show_current(self) -> None:
        """Cached lesson if there is one (no LLM call), a generating state, an error, or the card."""
        concept = self.current()
        if concept is None:
            return
        if concept.id in self.generating:
            self.show_markdown(f"# {concept.name}\n\nGenerating the lesson…", loading=True)
            return
        lesson = self.cache.get(concept.id)
        if lesson is not None:
            self.show_markdown(f"# {concept.name}\n\n{lesson.text}")
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
