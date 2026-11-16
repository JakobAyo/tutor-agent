from pathlib import Path

import batches
import pytest

from tutor_agent import detector, paths
from tutor_agent.events import Event, Kind
from tutor_agent.runner import ClaudeError
from tutor_agent.settings import Settings

EVENTS = batches.load("supervisor-loop")


def item(**kw):
    base = {
        "name": "Last-known-good rollback",
        "category": "Design patterns",
        "summary": "s",
        "why_here": "w",
        "event_index": 3,
        "reuses_known": False,
    }
    return {**base, **kw}


def ev(content: str, kind=Kind.EDIT) -> Event:
    return Event("s", None, "/p", "t", kind, "/p/f.py", content, "/t.jsonl:1")


def test_prompt_numbers_events_and_lists_known():
    prompt = detector.build_prompt(EVENTS, ["Retry with backoff", "Atomic file writes"])
    assert prompt.startswith('KNOWN: ["Atomic file writes", "Retry with backoff"]')
    assert "[3] edit ~/Projects/project-d/supervisor.py\n#!/usr/bin/env python3" in prompt
    assert f"[{len(EVENTS) - 1}] " in prompt


def test_schema_categories_are_the_curriculum():
    text = (Path(__file__).parents[1] / "docs/pedagogy/curriculum.md").read_text()
    for cat in detector.CATEGORIES:
        assert f"- {cat}" in text


def test_parse_valid_items():
    out = detector.parse(
        {"concepts": [item(), item(name="Canary run", category="Testing", event_index=8)]}, EVENTS
    )
    assert [c.name for c in out] == ["Last-known-good rollback", "Canary run"]
    assert out[0].event is EVENTS[3]


@pytest.mark.parametrize(
    "bad",
    [
        item(event_index=999),
        item(event_index=-1),
        item(event_index=True),
        item(event_index="3"),
        item(category="pattern"),
        item(name="  "),
        item(name="!!"),
        item(summary=None),
        item(reuses_known="no"),
        "not an object",
    ],
)
def test_invalid_item_is_dropped_others_kept(bad):
    out = detector.parse({"concepts": [bad, item(name="Kept")]}, EVENTS)
    assert [c.name for c in out] == ["Kept"]


@pytest.mark.parametrize("bad", [None, [], {"concepts": "x"}, {"other": []}])
def test_invalid_output_gives_nothing(bad):
    assert detector.parse(bad, EVENTS) == []
    assert "dropped" in paths.log_file().read_text()


def test_parse_caps_concepts_and_flattens_text():
    raw = [item(name=f"Concept\n {i}") for i in range(5)]
    out = detector.parse({"concepts": raw}, EVENTS)
    assert [c.name for c in out] == ["Concept 0", "Concept 1", "Concept 2"]


def test_snippet_keeps_first_lines():
    assert detector.snippet(ev("a\nb")) == "a\nb"
    cut = detector.snippet(ev("\n".join(f"line {i}" for i in range(100))))
    assert cut.splitlines()[:40] == [f"line {i}" for i in range(40)]
    assert cut.endswith("[... 60 more lines cut ...]")


def test_detect_calls_runner_with_schema_and_cheap_model(fake_claude):
    fake_claude.answer({"concepts": [item()]})
    cfg = Settings(detect_model="haiku-test", claude_bin=str(fake_claude.bin))
    out = detector.detect(EVENTS, ["Known thing"], cfg)
    assert [c.name for c in out] == ["Last-known-good rollback"]
    argv = fake_claude.record["argv"]
    assert argv[argv.index("--model") + 1] == "haiku-test"
    assert "--json-schema" in argv
    assert argv[argv.index("--system-prompt") + 1] == detector.SYSTEM_PROMPT
    assert 'KNOWN: ["Known thing"]' in fake_claude.record["stdin"]


def test_detect_raises_on_failed_call(fake_claude):
    fake_claude.mode("fail")
    with pytest.raises(ClaudeError):
        detector.detect(EVENTS, [], Settings(claude_bin=str(fake_claude.bin)))
