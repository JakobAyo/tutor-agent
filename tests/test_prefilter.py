import json
from pathlib import Path

import pytest
import transcripts as t

from tutor_agent.events import Event, EventMapper, Kind
from tutor_agent.prefilter import MIN_REASONING_CHARS, skip_reason

FIXTURES = sorted((Path(__file__).parent / "fixtures/batches").glob("*.json"))


def load_fixture(path: Path) -> list[Event]:
    return [Event(**{**e, "kind": Kind(e["kind"])}) for e in json.loads(path.read_text())]


def mapped(records) -> list[Event]:
    m = EventMapper()
    return [e for r in records for e in m.map(r, "x")]


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.stem)
def test_m0_batches_pass(fixture):
    """The M0 batches all held concepts worth detecting."""
    assert skip_reason(load_fixture(fixture)) is None


def test_empty_batch_is_skipped():
    assert skip_reason([]) == "no new events"


def test_short_chat_is_skipped():
    events = mapped([t.prompt("thanks!"), t.assistant(t.text("You're welcome."))])
    assert "no edits, no commands" in skip_reason(events)


def test_long_explanation_passes():
    events = mapped([t.prompt("why a queue?"), t.assistant(t.text("x" * MIN_REASONING_CHARS))])
    assert skip_reason(events) is None


def test_prompt_length_does_not_count_as_reasoning():
    events = mapped([t.prompt("y" * 5000), t.assistant(t.text("ok"))])
    assert skip_reason(events) is not None


@pytest.mark.parametrize("block", [
    t.tool_use("1", "Bash", command="ls"),
    t.tool_use("2", "Write", file_path="/a", content="b"),
])
def test_any_edit_or_command_passes(block):
    assert skip_reason(mapped([t.assistant(block)])) is None


def test_fixture_loader_matches_kinds():
    assert {e.kind for f in FIXTURES for e in load_fixture(f)} <= set(Kind)
