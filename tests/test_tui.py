"""The tutor pane, driven headless through Textual's pilot. The fake `claude` answers lessons."""

import asyncio

from textual.widgets import Markdown, OptionList

from tutor_agent import lessons
from tutor_agent.settings import Settings
from tutor_agent.store import ConceptStore, Entry, Source, Status
from tutor_agent.tui import TutorApp


def seed(*names: str) -> ConceptStore:
    store = ConceptStore()
    store.record([Entry(n, "Design patterns", f"About {n}.",
                        Source(snippet=f"code for {n}", context="ctx", project="/home/me/Projects/api"))
                  for n in names])
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
    ol = app.query_one(OptionList)
    return [str(ol.get_option_at_index(i).prompt).split("\n")[0] for i in range(ol.option_count)]


def shown(app) -> str:
    return app.query_one(Markdown).source


async def settle(pilot, app):
    await app.workers.wait_for_complete()
    await pilot.pause()


def test_empty_memory():
    async def t(pilot, app):
        assert "No concepts yet" in shown(app)
    run(t)


def test_list_is_grouped_new_first_and_hides_dismissed():
    store = seed("Alpha", "Beta", "Gamma", "Delta")
    store.set_status("beta", Status.UNDERSTOOD)
    store.set_status("gamma", Status.DISMISSED)
    store.set_status("delta", Status.SEEN)

    async def t(pilot, app):
        assert options(app) == ["NEW (1)", "Alpha", "SEEN (1)", "Delta", "UNDERSTOOD (1)", "Beta"]
        await pilot.press("h")
        assert options(app)[-2:] == ["DISMISSED (1)", "Gamma"]
    run(t, store)


def test_highlight_shows_card_without_a_call(fake_claude):
    store = seed("Alpha")

    async def t(pilot, app):
        assert "About Alpha." in shown(app) and "Enter" in shown(app)
        assert fake_claude.calls == 0
        assert store.get("alpha").status is Status.NEW
    run(t, store)


def test_open_marks_seen_generates_once_and_reopens_from_cache(fake_claude):
    store = seed("Alpha", "Beta")

    async def t(pilot, app):
        first = app.highlighted_id()
        await pilot.press("enter")
        await settle(pilot, app)
        assert fake_claude.calls == 1
        assert store.get(first).status is Status.SEEN
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
        assert store.get("alpha").status is Status.NEW
        await pilot.press("u")
        assert store.get("alpha").status is Status.UNDERSTOOD
        await pilot.press("s")
        assert store.get("alpha").status is Status.SEEN
        await pilot.press("d")
        assert store.get("alpha").status is Status.DISMISSED
        assert "Alpha" not in options(app)  # hidden by default
        await pilot.press("h")
        while app.highlighted_id() != "alpha":
            await pilot.press("down")
        await pilot.press("n")
        assert store.get("alpha").status is Status.NEW
    run(t, store)


def test_pane_picks_up_detector_writes():
    store = seed("Alpha")

    async def t(pilot, app):
        seed("Beta")  # another process would do this; the pane polls the file
        for _ in range(20):
            await pilot.pause(0.05)
            if "Beta" in options(app):
                break
        assert options(app)[:3] == ["NEW (2)", "Alpha", "Beta"] or options(app)[:3] == ["NEW (2)", "Beta", "Alpha"]
    run(t, store)


def test_pane_stays_responsive_while_generating(fake_claude):
    fake_claude.mode("hang")
    store = seed("Alpha", "Beta")

    async def t(pilot, app):
        app.cfg = Settings(claude_timeout_s=2)
        await pilot.press("enter")
        await pilot.pause()
        assert app.query_one(Markdown).loading
        await pilot.press("down", "down")  # the UI still handles keys during the call
        await pilot.press("u")
        assert sum(c.status is Status.UNDERSTOOD for c in store.list()) == 1
        await settle(pilot, app)
    run(t, store)
