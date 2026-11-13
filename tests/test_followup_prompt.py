"""Follow-up and "what just happened" quality with the real lesson model (Sonnet by default).
Two calls, so they only run with `-m prompt`. Checks the M5 "done when" items: a follow-up
refers to the lesson and builds on known concepts, no Claude Code session is created, and an
explanation of a real turn has the expected structure.
"""

import shutil
from pathlib import Path

import batches
import pytest

from tutor_agent import detector, explain, followups, paths
from tutor_agent.lessons import Lesson
from tutor_agent.settings import Settings
from tutor_agent.store import Concept, Source, Status

pytestmark = [pytest.mark.prompt, pytest.mark.skipif(shutil.which("claude") is None, reason="claude not installed")]


def session_files() -> set[Path]:
    return set(paths.claude_projects_dir().rglob("*.jsonl"))


def test_follow_up_refers_to_the_lesson_and_builds_on_known_concepts():
    event = batches.load("supervisor-loop")[3]  # the edit of supervisor.py
    source = Source(snippet=detector.snippet(event), project="~/Projects/project-d", file=event.file,
                    context="The agent wrote a loop that restarts the harness and rolls back to the "
                            "last good commit when the new one fails.")
    concept = Concept(id="supervisor-with-last-known-good-rollback", name="Supervisor with last-known-good rollback",
                      category="Design patterns", status=Status.SEEN, sources=[source],
                      summary="A parent process restarts a child and falls back to the last version that worked.")
    lesson = Lesson(concept.id, "## What the agent did\nThe supervisor runs harness.py in a loop and resets "
                    "to the last good commit when a run fails.\n\n## Why it did it\nSo a broken self-edit "
                    "can't stop the loop.", "sonnet", "t", source)
    known = [Concept(id="process-groups", name="Process groups", category="Language mechanisms",
                     status=Status.UNDERSTOOD, summary="Signal a whole tree of processes at once via its group id.")]

    before = session_files()
    answer = followups.answer(concept, lesson, [], known,
                              "How does the supervisor make sure a hanging harness run gets stopped?", Settings())
    assert session_files() == before, "the follow-up created a Claude Code session"

    assert "supervisor" in answer.lower() or "harness" in answer.lower(), answer
    assert "process group" in answer.lower(), f"does not build on the known concept:\n{answer}"
    assert len(answer.split()) < 450


def test_explanation_of_a_real_turn_has_the_structure():
    events = batches.load("supervisor-loop")
    turn = explain.LatestTurn(explain.Session("fixture", Path("fixture.jsonl"), 0, "~/Projects/project-d"), events)
    text = explain.explain(turn, [], Settings())

    sections = ("## What happened", "## Why it did it this way", "## Concepts behind it")
    positions = [text.find(s) for s in sections]
    assert all(p >= 0 for p in positions) and positions == sorted(positions), text
    assert "supervisor" in text.lower()
    assert len(text.split()) < 700
