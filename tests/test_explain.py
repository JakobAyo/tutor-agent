import os

import pytest
import transcripts as t

from tutor_agent import explain, paths
from tutor_agent.events import Kind
from tutor_agent.settings import Settings

T0, T1, T2 = "2026-11-12T10:00:00.000Z", "2026-11-12T11:00:00.000Z", "2026-11-12T11:00:05.000Z"


def session_file(sid=t.SESSION, project="-home-u-proj"):
    return paths.claude_projects_dir() / project / f"{sid}.jsonl"


def two_turns(path=None):
    """Turn 0 at T0, turn 1 at T1. Returns the transcript path."""
    return t.write(path or session_file(), t.turn(0, timestamp=T0) + t.turn(1, timestamp=T1))


def test_recent_sessions_newest_first_with_project_and_last_prompt():
    old = two_turns(session_file("old"))
    new = t.write(session_file("new", "-home-u-other"), [t.prompt("fix the build", cwd="/home/u/other")])
    os.utime(old, (1000, 1000))
    os.utime(new, (2000, 2000))
    sessions = explain.recent_sessions()
    assert [s.session_id for s in sessions] == ["new", "old"]
    assert sessions[0].project == "/home/u/other" and sessions[0].last_prompt == "fix the build"
    assert sessions[1].last_prompt == "add caching #1"
    assert sessions[0].label(now=2000 + 7200) == "other · 2 h ago\n  fix the build"
    assert len(explain.recent_sessions(limit=1)) == 1


def test_subagent_activity_makes_a_session_recent():
    a = two_turns(session_file("a"))
    b = two_turns(session_file("b"))
    sub = t.write(a.parent / "a" / "subagents" / "agent-x.jsonl", [t.prompt("sub task", agent_id="x")])
    os.utime(a, (1000, 1000))
    os.utime(b, (2000, 2000))
    os.utime(sub, (3000, 3000))
    assert [s.session_id for s in explain.recent_sessions()] == ["a", "b"]


def test_label_finds_a_prompt_far_back(monkeypatch):
    monkeypatch.setattr(explain, "TAIL_BYTES", 200)
    path = t.write(session_file(), [t.prompt("the real prompt")] +
                   [t.assistant(t.text("x" * 300)) for _ in range(20)])
    assert explain.describe(path, 0).last_prompt == "the real prompt"


def test_no_projects_dir_means_no_sessions():
    assert explain.recent_sessions() == []


def test_latest_turn_starts_at_the_last_prompt():
    path = two_turns()
    turn = explain.latest_turn(explain.describe(path, 0))
    assert turn.events[0].kind is Kind.PROMPT and turn.events[0].content == "add caching #1"
    assert all(e.timestamp == T1 for e in turn.events)
    assert [e.kind for e in turn.events] == [Kind.PROMPT, Kind.REASONING, Kind.EDIT, Kind.COMMAND,
                                             Kind.TOOL_RESULT, Kind.REASONING]


def test_injected_wrappers_do_not_start_a_new_turn():
    path = two_turns()
    t.write(path, [t.prompt("<task-notification>agent done</task-notification>", timestamp=T2),
                   t.assistant(t.text("The subagent finished."), timestamp=T2)], append=True)
    turn = explain.latest_turn(explain.describe(path, 0))
    assert turn.events[0].content == "add caching #1"
    assert turn.events[-1].content == "The subagent finished."


def test_latest_turn_includes_subagent_work_from_the_same_span():
    path = two_turns()
    t.write(path.parent / t.SESSION / "subagents" / "agent-x.jsonl", [
        t.assistant(t.text("old subagent work"), agent_id="x", timestamp=T0),
        t.assistant(t.tool_use("s1", "Bash", command="ruff check"), agent_id="x", timestamp=T2),
        t.tool_result("s1", "All checks passed", agent_id="x", timestamp=T2),
    ])
    turn = explain.latest_turn(explain.describe(path, 0))
    contents = [e.content for e in turn.events]
    assert "old subagent work" not in contents
    assert contents[-2:] == ["ruff check", "All checks passed"]  # after the main events, by time
    assert turn.subagent_events == 2


def test_fit_keeps_the_prompt_and_the_newest_events():
    path = t.write(session_file(), [t.prompt("go", timestamp=T1)] +
                   [t.assistant(t.text(f"step {i} " + "x" * 100), timestamp=T1) for i in range(10)])
    events = explain.latest_turn(explain.describe(path, 0)).events
    kept, dropped = explain.fit(events, budget=350)
    assert kept[0].content == "go"
    assert [e.content.split()[1] for e in kept[1:]] == ["7", "8", "9"] and dropped == 7
    kept, dropped = explain.fit(events, max_events=3)
    assert len(kept) == 3 and kept[0].content == "go" and dropped == 8


def test_explain_calls_the_lesson_model_with_the_turn_and_known_concepts(fake_claude):
    path = two_turns()
    t.write(path.parent / t.SESSION / "subagents" / "agent-x.jsonl",
            [t.assistant(t.text("subagent says hi"), agent_id="x", timestamp=T2)])
    turn = explain.latest_turn(explain.describe(path, 0))
    text = explain.explain(turn, [], Settings(lesson_model="opus"))
    argv = fake_claude.record["argv"]
    assert argv[argv.index("--model") + 1] == "opus"
    assert "## What happened" in argv[argv.index("--system-prompt") + 1]
    prompt = fake_claude.record["stdin"]
    assert "PROJECT: /home/u/proj" in prompt and "(none yet)" in prompt
    assert "- edit /home/u/proj/a.py\n--- old\nx\n+++ new\ny" in prompt
    assert "- reasoning (subagent x)\nsubagent says hi" in prompt
    assert text.startswith("echo: PROJECT:")


def test_turn_without_agent_activity_makes_no_call(fake_claude):
    path = t.write(session_file(), [t.prompt("just asked")])
    with pytest.raises(explain.ExplainError):
        explain.explain(explain.latest_turn(explain.describe(path, 0)), [], Settings())
    assert fake_claude.calls == 0
