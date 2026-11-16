"""The tutor pane (ADR 0009, 0028, 0035). Only `tutor tui` imports this module: Textual is heavy.

Left: status tabs (New, Seen, Understood, Dismissed, All), an optional filter line and search
line, and the concept list. What the list shows (tab, search, project, category, sort) comes from
`browse.py`. Right: the highlighted concept's cached lesson, or a short card. Enter opens a lesson
(marks it `seen`, generates it on first open). Under it, an input for follow-up questions (ADR
0012, 0029); the thread lives per concept while the pane is open. `w` picks a recent session and
explains its latest turn ("what just happened", F8). Vim motions move around; `?` lists every key.
Every model call runs in a worker thread, so the pane never freezes. The concept memory is
polled once a second, so concepts the detector adds show up without a restart.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import ClassVar

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Markdown, OptionList, Static, Tab, Tabs
from textual.widgets.option_list import Option, OptionDoesNotExist

from tutor_agent import browse, explain, followups, lessons, paths, settings
from tutor_agent.browse import Filters, project_name
from tutor_agent.log import get_logger
from tutor_agent.store import Concept, ConceptStore, Status, StoreError

# Which status keys apply to which current status (learner model, ADR 0018).
TRANSITIONS: dict[Status, set[Status]] = {
    Status.UNDERSTOOD: {Status.NEW, Status.SEEN},
    Status.SEEN: {Status.UNDERSTOOD},
    Status.DISMISSED: {Status.NEW, Status.SEEN, Status.UNDERSTOOD},
    Status.NEW: {Status.DISMISSED},  # undo a dismissal
}

HELP = """\
# Keys

## Move
| Key | |
|---|---|
| `j` / `k` | down / up (list or lesson) |
| `g` / `G` | top / bottom |
| `h` / `l` | focus the list / the lesson |
| `Ctrl-d` / `Ctrl-u` | scroll the lesson half a page |
| `1`–`5`, `[` / `]` | tab: New, Seen, Understood, Dismissed, All |
| `m` | full-width lesson (again to bring the list back) |

## Find
| Key | |
|---|---|
| `/` | search names and summaries (Enter keeps it, Esc clears it) |
| `p` / `c` | filter by project / category |
| `o` | next sort order: newest, oldest, most seen, A–Z |
| `Esc` | on the list: clear all filters |

## Learn
| Key | |
|---|---|
| `Enter` | open the lesson (marks it seen) |
| `f` | ask a follow-up about the open lesson |
| `r` | regenerate the lesson |
| `w` / `x` | explain what just happened in a session / show it again |

## Status
| Key | |
|---|---|
| `u` | understood |
| `s` | back to seen |
| `d` / `n` | dismiss / undo a dismissal |
| `z` | undo the last status change |

`q` quits. `Esc` or `?` closes this.
"""  # noqa: RUF001  # the en dashes are intended


def card(concept: Concept) -> str:
    source = concept.sources[-1] if concept.sources else None
    lines = [
        f"# {concept.name}",
        "",
        f"*{concept.category}* · **{concept.status}** · {project_name(concept)} · "
        f"seen {len(concept.sources)}×",  # noqa: RUF001  # the multiplication sign is intended
        "",
        concept.summary,
    ]
    if source:
        lines += ["", f"> {source.context}"]
    lines += ["", "Press **Enter** to open the lesson."]
    return "\n".join(lines)


def row(concept: Concept) -> Text:
    label = Text()  # not Text(icon, style=...): that styles the whole row
    label.append(browse.ICONS[concept.status], style=browse.STYLES[concept.status])
    label.append(f" {concept.name}")
    label.append(f"\n  {concept.category} · {project_name(concept)}", style="dim")
    return label


def thread_markdown(thread: list[followups.Turn], pending: str | None) -> str:
    if not thread and pending is None:
        return ""
    parts = ["", "---", "", "## Follow-ups"]
    for t in thread:
        parts += ["", f"**You:** {t.question}", "", t.answer]
    if pending is not None:
        parts += ["", f"**You:** {pending}", "", "*Thinking…*"]
    return "\n".join(parts)


class ConceptList(OptionList):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g", "first", "Top", show=False),
        Binding("G", "last", "Bottom", show=False),
    ]


class LessonPane(VerticalScroll):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("j", "scroll_down", "Down", show=False),
        Binding("k", "scroll_up", "Up", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G", "scroll_end", "Bottom", show=False),
    ]


class SessionPicker(ModalScreen[explain.Session | None]):
    """Pick one of the recently active sessions. Enter picks, Escape cancels."""

    CSS = """
    SessionPicker { align: center middle; }
    #sessions { width: 90; max-height: 24; border: round $primary; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, sessions: list[explain.Session]) -> None:
        super().__init__()
        self.sessions = sessions

    def compose(self) -> ComposeResult:
        ol = ConceptList(
            *(Option(s.label(), id=str(i)) for i, s in enumerate(self.sessions)), id="sessions"
        )
        ol.border_title = "What just happened in…"
        yield ol

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        if event.option_id is not None:  # every option is created with an id
            self.dismiss(self.sessions[int(event.option_id)])

    def action_cancel(self) -> None:
        self.dismiss(None)


ANY = ""  # what ChoicePicker returns for "any"; None means cancelled


class ChoicePicker(ModalScreen[str | None]):
    """Pick one value for a filter, or "any". Enter picks, Escape cancels."""

    CSS = """
    ChoicePicker { align: center middle; }
    #choices { width: 50; max-height: 20; border: round $primary; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, choices: list[str], current: str | None) -> None:
        super().__init__()
        self.title_text = title
        self.choices = [ANY, *choices]
        self.current = current or ANY

    def compose(self) -> ComposeResult:
        ol = ConceptList(
            *(
                Option(Text(c or "any", style="italic" if c == ANY else ""), id=str(i))
                for i, c in enumerate(self.choices)
            ),
            id="choices",
        )
        ol.border_title = self.title_text
        ol.highlighted = self.choices.index(self.current) if self.current in self.choices else 0
        yield ol

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        if event.option_id is not None:  # every option is created with an id
            self.dismiss(self.choices[int(event.option_id)])

    def action_cancel(self) -> None:
        self.dismiss(None)


class HelpScreen(ModalScreen[None]):
    CSS = """
    HelpScreen { align: center middle; }
    #help { width: 76; max-height: 90%; border: round $primary; padding: 0 2; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape,question_mark,q", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with LessonPane(id="help"):
            yield Markdown(HELP)

    def action_close(self) -> None:
        self.dismiss(None)


class TutorApp(App[None]):
    TITLE = "Tutor"
    CSS = """
    #sidebar { width: 54; border-right: solid $primary-background; }
    #tabs { height: 2; }
    #chips { color: $text-muted; padding: 0 1; }
    #search, #chips { display: none; }
    #concepts { height: 1fr; border: none; }
    #lesson-pane { padding: 0 2; }
    #ask { dock: bottom; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("slash", "search", "Search"),
        Binding("u", "set_status('understood')", "Understood"),
        Binding("f", "ask", "Follow-up"),
        Binding("w", "what_happened", "What just happened"),
        Binding("question_mark", "help", "Keys"),
        Binding("q", "quit", "Quit"),
        Binding("s", "set_status('seen')", "Back to seen", show=False),
        Binding("d", "set_status('dismissed')", "Dismiss", show=False),
        Binding("n", "set_status('new')", "Undo dismiss", show=False),
        Binding("z", "undo", "Undo status", show=False),
        Binding("r", "regenerate", "Regenerate", show=False),
        Binding("x", "show_explanation", "Last explanation", show=False),
        Binding("p", "pick_project", "Project", show=False),
        Binding("c", "pick_category", "Category", show=False),
        Binding("o", "next_sort", "Sort", show=False),
        Binding("m", "toggle_wide", "Full width", show=False),
        Binding("h", "focus_list", "Focus list", show=False),
        Binding("l", "focus_lesson", "Focus lesson", show=False),
        Binding("ctrl+d", "half_page(1)", "Scroll down", show=False),
        Binding("ctrl+u", "half_page(-1)", "Scroll up", show=False),
        Binding("left_square_bracket", "step_tab(-1)", "Previous tab", show=False),
        Binding("right_square_bracket", "step_tab(1)", "Next tab", show=False),
        *(
            Binding(str(i + 1), f"tab({i})", browse.tab_title(t), show=False)
            for i, t in enumerate(browse.TABS)
        ),
        Binding("escape", "escape", "Back", show=False),
    ]

    def __init__(
        self,
        store: ConceptStore | None = None,
        cache: lessons.LessonCache | None = None,
        cfg: settings.Settings | None = None,
        poll_s: float = 1.0,
    ) -> None:
        super().__init__()
        self.store = store or ConceptStore()
        self.cache = cache or lessons.LessonCache()
        self.cfg = cfg or settings.load()
        self.poll_s = poll_s
        self.tab: Status | None = browse.TABS[0]
        self.filters = Filters()
        self.wide = False  # the list is hidden, the lesson uses the full width
        # Concepts opened on this tab visit stay listed although opening moved them to `seen`,
        # so Enter in the New tab doesn't make the lesson's row jump away. Cleared on tab change.
        self.opened_here: set[str] = set()
        self.last_change: tuple[str, Status] | None = None  # (concept id, status before), for `z`
        self.concepts: dict[str, Concept] = {}
        self.generating: set[str] = set()
        self.errors: dict[str, str] = {}  # last failed generation per concept, shown until retried
        self.threads: dict[
            str, list[followups.Turn]
        ] = {}  # follow-ups per concept, kept while open
        self.asking: dict[str, str] = {}  # concept id -> the question being answered
        self.explaining: explain.Session | None = None
        self.explanation: tuple[explain.Session, str] | None = None  # the last one, for `x`
        self.showing_explanation = False  # the right side shows an explanation, not a concept
        self._highlighted: str | None = None
        self._stamp: tuple[int, int] | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            # Kept as attributes: `query_one` searches the active screen, which is a picker
            # while one is open.
            with Vertical(id="sidebar") as self.sidebar:
                self.tabs = Tabs(
                    *(Tab(browse.tab_title(t), id=browse.tab_id(t)) for t in browse.TABS),
                    id="tabs",
                )
                self.tabs.can_focus = False  # tabs switch with keys; focus stays on the list
                yield self.tabs
                self.chips = Static(id="chips")
                yield self.chips
                self.search_input = Input(
                    placeholder="search… (Enter: keep, Esc: clear)", id="search"
                )
                yield self.search_input
                self.concept_list = ConceptList(id="concepts")
                yield self.concept_list
            with Vertical():
                with LessonPane(id="lesson-pane") as self.lesson_pane:
                    self.lesson_md = Markdown(id="lesson")
                    yield self.lesson_md
                self.ask_input = Input(
                    placeholder="f: ask a follow-up about the open lesson · Esc: back", id="ask"
                )
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
        self.refresh_list()

    def listed(self) -> list[Concept]:
        """The current tab's concepts after the filters, plus the ones opened on this visit."""
        everything = list(self.concepts.values())
        shown = browse.visible(everything, self.tab, self.filters)
        ids = {c.id for c in shown}
        extra = [
            c
            for c in everything
            if c.id in self.opened_here
            and c.id not in ids
            and c.status is not Status.DISMISSED
            and browse.matches(c, self.filters)
        ]
        return browse.sort(shown + extra, self.filters.sort) if extra else shown

    def refresh_list(self) -> None:
        """Rebuild tabs, filter line, and list. A concept that left the list (a status change)
        hands the highlight to the row that took its place."""
        everything = list(self.concepts.values())
        counts = browse.counts(everything, self.filters)
        for t in browse.TABS:
            self.tabs.query_one(
                f"#{browse.tab_id(t)}", Tab
            ).label = f"{browse.tab_title(t)} {counts[t]}"
        self.chips.update(f"{self.filters.chips()}  (Esc clears)")
        self.chips.display = self.filters.active
        self.sub_title = f"{sum(c.status is Status.NEW for c in everything)} new"

        option_list = self.concept_list
        keep = self.highlighted_id()
        index = option_list.highlighted or 0
        option_list.clear_options()
        option_list.add_options(Option(row(c), id=c.id) for c in self.listed())
        self.highlight(keep, fallback=index)

    def highlight(self, cid: str | None, fallback: int = 0) -> None:
        option_list = self.concept_list
        index: int | None = None
        if cid is not None:
            try:
                index = option_list.get_option_index(cid)
            except OptionDoesNotExist:  # moved to another tab, filtered out, or gone
                index = None
        if index is None and option_list.option_count:
            index = min(fallback, option_list.option_count - 1)
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
            return  # a picker's list
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

    # --- tabs, search, filters (ADR 0035) -----------------------------------------------------

    def switch_tab(self, tab: Status | None) -> None:
        if tab == self.tab:
            return
        self.tab = tab
        self.opened_here.clear()
        self.tabs.active = browse.tab_id(tab)
        self.concept_list.highlighted = None  # a new tab starts at its top
        self.refresh_list()

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        # A click on a tab. Keys go through `switch_tab`, which sets `active` itself.
        if event.tab.id is not None:
            self.switch_tab(next(t for t in browse.TABS if browse.tab_id(t) == event.tab.id))

    def action_tab(self, index: int) -> None:
        self.switch_tab(browse.TABS[index])

    def action_step_tab(self, step: int) -> None:
        i = browse.TABS.index(self.tab)
        self.switch_tab(browse.TABS[(i + step) % len(browse.TABS)])

    def set_filters(self, filters: Filters) -> None:
        self.filters = filters
        self.refresh_list()

    def action_search(self) -> None:
        self.leave_wide()
        self.search_input.display = True
        self.search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input is self.search_input and event.value != self.filters.query:
            self.set_filters(replace(self.filters, query=event.value))

    def close_search(self, clear: bool) -> None:
        if clear:
            self.search_input.value = ""
            self.set_filters(replace(self.filters, query=""))
        self.search_input.display = bool(self.search_input.value)
        self.concept_list.focus()

    def action_pick_project(self) -> None:
        choices = browse.projects(list(self.concepts.values()))
        self.push_screen(
            ChoicePicker("Project", choices, self.filters.project),
            lambda v: self._picked(v, "project"),
        )

    def action_pick_category(self) -> None:
        choices = browse.categories(list(self.concepts.values()))
        self.push_screen(
            ChoicePicker("Category", choices, self.filters.category),
            lambda v: self._picked(v, "category"),
        )

    def _picked(self, value: str | None, field: str) -> None:
        if value is not None:  # None: cancelled
            choice = value or None  # ANY ("") drops the filter
            if field == "project":
                self.set_filters(replace(self.filters, project=choice))
            else:
                self.set_filters(replace(self.filters, category=choice))

    def action_next_sort(self) -> None:
        self.set_filters(self.filters.next_sort())
        self.notify(f"Sort: {self.filters.sort}")

    def action_escape(self) -> None:
        """Escape: leave an input, else clear the filters."""
        focused = self.focused
        if focused is self.search_input:
            self.close_search(clear=True)
        elif focused is self.concept_list and self.filters.active:
            self.search_input.value = ""
            self.search_input.display = False
            self.set_filters(Filters())
            self.notify("Filters cleared")
        else:
            self.action_focus_list()

    # --- moving around (ADR 0035) ---------------------------------------------------------------

    def action_focus_list(self) -> None:
        self.leave_wide()
        self.concept_list.focus()

    def action_focus_lesson(self) -> None:
        self.lesson_pane.focus()

    def action_toggle_wide(self) -> None:
        self.wide = not self.wide
        self.sidebar.display = not self.wide
        if self.wide:
            self.lesson_pane.focus()
        else:
            self.concept_list.focus()

    def leave_wide(self) -> None:
        if self.wide:
            self.wide = False
            self.sidebar.display = True

    def action_half_page(self, direction: int) -> None:
        pane = self.lesson_pane
        pane.scroll_relative(y=direction * max(1, pane.size.height // 2), animate=False)

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

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

    def empty_text(self) -> str:
        if not self.concepts:
            return "# No concepts yet\n\nThey appear here as the detector finds them."
        where = f"{browse.tab_title(self.tab).lower()} concepts" if self.tab else "concepts"
        if self.filters.active:
            return f"# Nothing here\n\nNo {where} match the filters. Press **Esc** to clear them."
        return f"# Nothing here\n\nNo {where}. Switch tabs with **1**–**5** or **[** / **]**."  # noqa: RUF001

    def show_current(self, scroll_end: bool = False) -> None:
        """Cached lesson (no LLM call), a generating state, an error, or the card."""
        if self.showing_explanation:
            return
        concept = self.current()
        if concept is None:
            self.show_markdown(self.empty_text())
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
        self.opened_here.add(cid)
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
        # Worker thread: any failure is shown in the pane and logged, it must not kill the TUI.
        except Exception as e:  # noqa: BLE001  # ClaudeError, LessonError, OSError, ...
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

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input is self.search_input:
            self.close_search(clear=False)
            return
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
        self.answer_followup(
            concept, lesson, list(self.threads.get(concept.id, [])), known, question
        )
        self.show_current(scroll_end=True)

    @work(thread=True, group="followups")
    def answer_followup(
        self,
        concept: Concept,
        lesson: lessons.Lesson,
        thread: list[followups.Turn],
        known: list[Concept],
        question: str,
    ) -> None:
        try:
            text, error = (
                followups.answer(
                    concept,
                    lesson,
                    thread=thread,
                    known=known,
                    question=question,
                    settings=self.cfg,
                ),
                None,
            )
        # Worker thread: any failure is shown as a notification and logged.
        except Exception as e:  # noqa: BLE001  # ClaudeError, FollowUpError, ...
            get_logger().exception("follow-up failed for %s", concept.id)
            text, error = None, str(e) or type(e).__name__
        self.call_from_thread(self.followup_done, concept.id, question, text, error)

    def followup_done(self, cid: str, question: str, text: str | None, error: str | None) -> None:
        self.asking.pop(cid, None)
        if text is None:  # the worker sets `error` exactly when there is no text
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
        self.show_markdown(
            f"# What just happened\n\n{session.label()}\n\nReading the latest turn…", loading=True
        )
        self.explain_turn(session, followups.known_concepts(list(self.concepts.values())))

    @work(thread=True, group="explain")
    def explain_turn(self, session: explain.Session, known: list[Concept]) -> None:
        try:
            turn = explain.latest_turn(session)
            text, error = explain.explain(turn, known, self.cfg), None
            if turn.dropped_events:
                text += (
                    f"\n\n*{turn.dropped_events} earlier events of this long turn were left out.*"
                )
        # Worker thread: any failure is shown as a notification and logged.
        except Exception as e:  # noqa: BLE001  # OSError, ClaudeError, ExplainError, ...
            get_logger().exception("explanation failed for %s", session.transcript)
            text, error = None, str(e) or type(e).__name__
        self.call_from_thread(self.explanation_done, session, text, error)

    def explanation_done(
        self, session: explain.Session, text: str | None, error: str | None
    ) -> None:
        self.explaining = None
        if text is None:  # the worker sets `error` exactly when there is no text
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
        self.show_markdown(
            f"# What just happened\n\n*{project} · session {session.session_id[:8]}*\n\n{text}"
        )

    # --- status actions -----------------------------------------------------------------------

    def action_set_status(self, status: str) -> None:
        target = Status(status)
        concept = self.current()
        if concept is None:
            return
        if concept.status not in TRANSITIONS[target]:
            self.notify(f"Can't go from {concept.status} to {target}.", severity="warning")
            return
        self.last_change = (concept.id, concept.status)
        self.opened_here.discard(concept.id)  # a status change moves it out of this tab
        self._change(lambda: self.store.set_status(concept.id, target))
        self.notify(f"{browse.ICONS[target]} {concept.name}: {target} · z to undo")

    def action_undo(self) -> None:
        if self.last_change is None:
            self.notify("Nothing to undo.", severity="warning")
            return
        cid, before = self.last_change
        self.last_change = None
        self._change(lambda: self.store.set_status(cid, before))
        concept = self.concepts.get(cid)
        if concept is not None:
            self.highlight(cid, fallback=self.concept_list.highlighted or 0)
            self.notify(f"{browse.ICONS[before]} {concept.name}: back to {before}")

    def _change(self, write: Callable[[], object]) -> None:
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
