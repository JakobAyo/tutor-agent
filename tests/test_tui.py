"""The tutor pane, driven headless through Textual's pilot. The fake `claude` answers lessons."""

import asyncio

import transcripts
from textual.widgets import Input, Markdown, OptionList, Tab

from tutor_agent import lessons
from tutor_agent.settings import Settings
from tutor_agent.store import Concept, ConceptStore, Entry, Source, Status
from tutor_agent.tui import ChoicePicker, HelpScreen, SessionPicker, TutorApp


def get(store: ConceptStore, cid: str) -> Concept:
    concept = store.get(cid)
    assert concept is not None, f"{cid} not in the store"
    return concept


def seed(*names: str) -> ConceptStore:
    store = ConceptStore()
    store.record(
        [
            Entry(
                n,
                "Design patterns",
                f"About {n}.",
                Source(snippet=f"code for {n}", context="ctx", project="/home/me/Projects/api"),
            )
            for n in names
        ]
    )
    return store


def run(test, store=None, size=(120, 40)):
    """Run `test(pilot, app)` inside a headless app."""

    async def main():
        app = TutorApp(store=store or ConceptStore(), cfg=Settings(), poll_s=0.05)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            await test(pilot, app)

    asyncio.run(main())


def options(app) -> list[str]:
    """Concept names in the list, without the status icon."""
    ol = app.concept_list
    return [
        str(ol.get_option_at_index(i).prompt).split("\n")[0][2:] for i in range(ol.option_count)
    ]


def tab_labels(app) -> list[str]:
    return [str(tab.label) for tab in app.query(Tab)]


def shown(app) -> str:
    source: str = app.query_one("#lesson", Markdown).source
    return source


async def settle(pilot, app):
    await app.workers.wait_for_complete()
    await pilot.pause()


def test_empty_memory():
    async def t(pilot, app):
        assert "No concepts yet" in shown(app)

    run(t)


def test_tabs_list_one_status_each_with_counts():
    store = seed("Alpha", "Beta", "Gamma", "Delta")
    store.set_status("beta", Status.UNDERSTOOD)
    store.set_status("gamma", Status.DISMISSED)
    store.set_status("delta", Status.SEEN)

    async def t(pilot, app):
        assert options(app) == ["Alpha"]  # opens on New
        assert tab_labels(app) == ["New 1", "Seen 1", "Understood 1", "Dismissed 1", "All 4"]
        await pilot.press("2")
        assert options(app) == ["Delta"]
        await pilot.press("right_square_bracket")
        assert options(app) == ["Beta"]
        await pilot.press("right_square_bracket")
        assert options(app) == ["Gamma"]
        await pilot.press("5")
        assert sorted(options(app)) == ["Alpha", "Beta", "Delta", "Gamma"]
        await pilot.press("right_square_bracket")  # wraps around to New
        assert options(app) == ["Alpha"]
        await pilot.press("left_square_bracket")
        assert app.tab is None

    run(t, store)


def test_highlight_shows_card_without_a_call(fake_claude):
    store = seed("Alpha")

    async def t(pilot, app):
        assert "About Alpha." in shown(app) and "Enter" in shown(app)
        assert fake_claude.calls == 0
        assert get(store, "alpha").status is Status.NEW

    run(t, store)


def test_open_marks_seen_generates_once_and_reopens_from_cache(fake_claude):
    store = seed("Alpha", "Beta")

    async def t(pilot, app):
        first = app.highlighted_id()
        await pilot.press("enter")
        await settle(pilot, app)
        assert fake_claude.calls == 1
        assert get(store, first).status is Status.SEEN
        assert "echo: CONCEPT:" in shown(app)
        assert lessons.LessonCache().get(first) is not None

        other = "beta" if first == "alpha" else "alpha"
        app.highlight(other)
        assert "Enter" in shown(app)  # the other one has no lesson yet
        app.highlight(first)
        await pilot.press("enter")
        await settle(pilot, app)
        assert fake_claude.calls == 1  # reopened from the cache, no LLM call
        assert "echo: CONCEPT:" in shown(app)

    run(t, store)


def test_regenerate_makes_a_new_call(fake_claude):
    store = seed("Alpha")

    async def t(pilot, app):
        await pilot.press("enter")
        await settle(pilot, app)
        await pilot.press("r")
        await settle(pilot, app)
        assert fake_claude.calls == 2

    run(t, store)


def test_failed_lesson_is_shown_and_nothing_cached(fake_claude):
    fake_claude.mode("fail")
    store = seed("Alpha")

    async def t(pilot, app):
        await pilot.press("enter")
        await settle(pilot, app)
        assert "Lesson failed" in shown(app)
        assert lessons.LessonCache().get("alpha") is None

    run(t, store)


def test_status_keys_follow_the_learner_model():
    store = seed("Alpha")

    async def t(pilot, app):
        await pilot.press("s")  # new -> seen is not a key: opening does that
        assert get(store, "alpha").status is Status.NEW
        await pilot.press("u")
        assert get(store, "alpha").status is Status.UNDERSTOOD
        assert options(app) == []  # it left the New tab
        await pilot.press("3", "s")
        assert get(store, "alpha").status is Status.SEEN
        await pilot.press("2", "d")
        assert get(store, "alpha").status is Status.DISMISSED
        assert "Alpha" not in options(app)  # only in the Dismissed and All tabs
        await pilot.press("4", "n")
        assert get(store, "alpha").status is Status.NEW

    run(t, store)


def test_undo_restores_the_last_status_change():
    store = seed("Alpha", "Beta")

    async def t(pilot, app):
        await pilot.press("z")  # nothing to undo yet
        first = app.highlighted_id()
        await pilot.press("d")
        assert len(options(app)) == 1
        await pilot.press("z")
        assert get(store, first).status is Status.NEW
        assert app.highlighted_id() == first  # back in the list and highlighted
        await pilot.press("z")  # only one level
        assert get(store, first).status is Status.NEW

    run(t, store)


def test_pane_picks_up_detector_writes():
    store = seed("Alpha")

    async def t(pilot, app):
        seed("Beta")  # another process would do this; the pane polls the file
        for _ in range(20):
            await pilot.pause(0.05)
            if "Beta" in options(app):
                break
        assert sorted(options(app)) == ["Alpha", "Beta"]
        assert tab_labels(app)[0] == "New 2"

    run(t, store)


def test_pane_stays_responsive_while_generating(fake_claude):
    fake_claude.mode("hang")
    store = seed("Alpha", "Beta")

    async def t(pilot, app):
        app.cfg = Settings(claude_timeout_s=2)
        await pilot.press("enter")
        await pilot.pause()
        assert app.query_one("#lesson", Markdown).loading
        await pilot.press("down", "down")  # the UI still handles keys during the call
        await pilot.press("u")
        assert sum(c.status is Status.UNDERSTOOD for c in store.list()) == 1
        await settle(pilot, app)

    run(t, store)


# --- follow-ups (M5) ---------------------------------------------------------------------------


async def open_lesson(pilot, app):
    await pilot.press("enter")
    await settle(pilot, app)


async def ask(pilot, app, question):
    await pilot.press("f")
    for ch in question:
        await pilot.press("space" if ch == " " else ch)
    await pilot.press("enter")
    await settle(pilot, app)


def test_follow_up_thread_builds_on_the_lesson_and_known_concepts(fake_claude):
    store = seed("Alpha", "Beta")
    store.set_status("beta", Status.UNDERSTOOD)

    async def t(pilot, app):
        await pilot.press("5")  # All: Beta is understood
        app.highlight("alpha")
        await open_lesson(pilot, app)
        await ask(pilot, app, "why this")
        assert fake_claude.calls == 2
        prompt = fake_claude.record["stdin"]
        assert "LESSON (what the learner just read):\necho: CONCEPT: Alpha" in prompt
        assert "- Beta [understood]: About Beta." in prompt
        assert prompt.endswith("QUESTION:\nwhy this")
        assert "**You:** why this" in shown(app) and "## Follow-ups" in shown(app)

        await ask(pilot, app, "and then")
        assert (
            "Q: why this\nA: echo: CONCEPT: Alpha" in fake_claude.record["stdin"]
        )  # the thread so far
        assert shown(app).count("**You:**") == 2

        app.highlight("beta")
        assert "**You:**" not in shown(app)  # threads are per lesson
        app.highlight("alpha")
        assert shown(app).count("**You:**") == 2

    run(t, store)


def test_follow_up_keys_type_into_the_input_not_the_status_keys(fake_claude):
    store = seed("Alpha")

    async def t(pilot, app):
        await open_lesson(pilot, app)
        await ask(pilot, app, "uds")  # u, d, s are status keys outside the input
        assert get(store, "alpha").status is Status.SEEN
        assert fake_claude.record["stdin"].endswith("QUESTION:\nuds")
        await pilot.press("escape")
        assert app.focused is app.query_one(OptionList)

    run(t, store)


def test_follow_up_needs_an_open_lesson(fake_claude):
    store = seed("Alpha")

    async def t(pilot, app):
        await ask(pilot, app, "why")
        assert fake_claude.calls == 0
        assert "**You:**" not in shown(app)

    run(t, store)


def test_failed_follow_up_keeps_the_question(fake_claude):
    store = seed("Alpha")

    async def t(pilot, app):
        await open_lesson(pilot, app)
        fake_claude.mode("fail")
        await ask(pilot, app, "why")
        assert "**You:**" not in shown(app)
        assert app.query_one("#ask", Input).value == "why"

    run(t, store)


# --- what just happened (M5) -------------------------------------------------------------------


def write_session():
    from tutor_agent import paths

    return transcripts.write(
        paths.claude_projects_dir() / "-home-u-proj" / f"{transcripts.SESSION}.jsonl",
        transcripts.turn(0) + transcripts.turn(1),
    )


def test_what_just_happened_explains_the_picked_session(fake_claude):
    write_session()
    store = seed("Alpha")

    async def t(pilot, app):
        await pilot.press("w")
        await pilot.pause()
        assert isinstance(app.screen, SessionPicker)
        await pilot.press("enter")
        await settle(pilot, app)
        assert fake_claude.calls == 1
        assert "add caching #1" in fake_claude.record["stdin"]
        assert "# What just happened" in shown(app) and "echo: PROJECT: /home/u/proj" in shown(app)

        seed("Beta")  # a detector write reloads the list but keeps the explanation
        for _ in range(10):
            await pilot.pause(0.05)
        assert "echo: PROJECT:" in shown(app)

        await pilot.press("down", "down")  # moving in the list goes back to the concept
        assert "# What just happened" not in shown(app)
        await pilot.press("x")
        assert "echo: PROJECT:" in shown(app)
        assert fake_claude.calls == 1

    run(t, store)


def test_session_picker_can_be_cancelled(fake_claude):
    write_session()

    async def t(pilot, app):
        await pilot.press("w")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, SessionPicker)
        assert fake_claude.calls == 0

    run(t, seed("Alpha"))


def test_what_just_happened_without_sessions(fake_claude):
    async def t(pilot, app):
        await pilot.press("w")
        await pilot.pause()
        assert not isinstance(app.screen, SessionPicker)

    run(t)


# --- tabs, search, filters, vim keys (ADR 0035) -------------------------------------------------


def seed_mixed() -> ConceptStore:
    store = ConceptStore()
    store.record(
        [
            Entry(name, category, summary, Source(snippet="x", context="c", project=project))
            for name, category, summary, project in [
                ("File locking", "Mechanisms", "Advisory flock on a lock file.", "/p/api"),
                ("Dependency injection", "Design patterns", "Pass collaborators in.", "/p/web"),
                ("Worker threads", "Mechanisms", "Keep the UI responsive.", "/p/web"),
            ]
        ]
    )
    return store


async def type_text(pilot, text):
    for ch in text:
        await pilot.press("space" if ch == " " else ch)


def test_search_narrows_as_you_type_and_esc_clears():
    async def t(pilot, app):
        await pilot.press("slash")
        assert app.focused is app.search_input
        await type_text(pilot, "flk")  # fuzzy: f…l…k in "File locking"
        assert options(app) == ["File locking"]
        assert "/ flk" in str(app.chips.render())
        await pilot.press("enter")  # keeps the filter, back to the list
        assert app.focused is app.concept_list and options(app) == ["File locking"]
        await pilot.press("slash")
        await pilot.press("escape")  # clears the search
        assert len(options(app)) == 3 and not app.search_input.display

        await pilot.press("slash")
        await type_text(pilot, "responsive")  # summary match
        assert options(app) == ["Worker threads"]
        await pilot.press("enter", "escape")  # Esc on the list clears every filter
        assert len(options(app)) == 3 and not app.filters.active

    run(t, seed_mixed())


def test_search_with_no_match_says_so():
    async def t(pilot, app):
        await pilot.press("slash")
        await type_text(pilot, "zzz")
        assert options(app) == []
        assert "match the filters" in shown(app)
        assert tab_labels(app)[0] == "New 0"

    run(t, seed_mixed())


def test_project_and_category_pickers_filter_the_list():
    async def t(pilot, app):
        await pilot.press("p")
        await pilot.pause()
        assert isinstance(app.screen, ChoicePicker)
        await pilot.press("j", "j", "enter")  # any, api, web -> web
        await pilot.pause()
        assert sorted(options(app)) == ["Dependency injection", "Worker threads"]
        await pilot.press("c")
        await pilot.pause()
        await pilot.press("j", "j", "enter")  # any, Design patterns, Mechanisms
        await pilot.pause()
        assert options(app) == ["Worker threads"]
        chips = str(app.chips.render())
        assert "project: web" in chips and "category: Mechanisms" in chips

        await pilot.press("c")
        await pilot.pause()
        await pilot.press("escape")  # cancel keeps the filter
        await pilot.pause()
        assert options(app) == ["Worker threads"]
        await pilot.press("c")
        await pilot.pause()
        await pilot.press("g", "enter")  # "any" drops it
        await pilot.pause()
        assert len(options(app)) == 2

    run(t, seed_mixed())


def test_sort_cycles():
    async def t(pilot, app):
        await pilot.press("o", "o", "o")  # newest -> oldest -> most seen -> A-Z
        assert options(app) == ["Dependency injection", "File locking", "Worker threads"]
        assert app.chips.display
        await pilot.press("o")  # back to newest, so no filter line
        assert not app.chips.display

    run(t, seed_mixed())


def test_vim_motions_move_the_list_and_focus():
    async def t(pilot, app):
        await pilot.press("o", "o", "o")  # A-Z for a known order
        await pilot.press("j")
        assert app.highlighted_id() == "file-locking"
        await pilot.press("G")
        assert app.highlighted_id() == "worker-threads"
        await pilot.press("k", "g")
        assert app.highlighted_id() == "dependency-injection"
        await pilot.press("l")
        assert app.focused is app.lesson_pane
        await pilot.press("j", "ctrl+d", "ctrl+u")  # scroll the lesson; the list stays put
        assert app.highlighted_id() == "dependency-injection"
        await pilot.press("h")
        assert app.focused is app.concept_list

    run(t, seed_mixed(), size=(120, 12))


def test_full_width_lesson_toggles_the_list():
    async def t(pilot, app):
        await pilot.press("m")
        assert not app.sidebar.display and app.focused is app.lesson_pane
        await pilot.press("m")
        assert app.sidebar.display and app.focused is app.concept_list
        await pilot.press("m", "h")  # focusing the list brings it back too
        assert app.sidebar.display

    run(t, seed_mixed())


def test_help_overlay_opens_and_closes():
    async def t(pilot, app):
        await pilot.press("question_mark")
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("q")  # closes the overlay, doesn't quit
        await pilot.pause()
        assert app.is_running
        assert not isinstance(app.screen, HelpScreen)

    run(t, seed_mixed())


def test_opened_concept_stays_in_new_until_the_tab_changes(fake_claude):
    store = seed("Alpha", "Beta")

    async def t(pilot, app):
        first = app.highlighted_id()
        await open_lesson(pilot, app)
        assert get(store, first).status is Status.SEEN
        assert len(options(app)) == 2 and app.highlighted_id() == first  # no jump
        assert tab_labels(app)[:2] == ["New 1", "Seen 1"]
        await pilot.press("2", "1")
        assert len(options(app)) == 1

    run(t, store)


def test_empty_tab_says_how_to_move_on():
    async def t(pilot, app):
        await pilot.press("3")
        assert "No understood concepts" in shown(app)

    run(t, seed("Alpha"))


def test_clicking_a_tab_switches_to_it():
    store = seed("Alpha")
    store.set_status("alpha", Status.SEEN)

    async def t(pilot, app):
        await pilot.click("#tab-seen")
        await pilot.pause()
        assert app.tab is Status.SEEN and options(app) == ["Alpha"]

    run(t, store)
