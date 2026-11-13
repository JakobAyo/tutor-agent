import pytest

from tutor_agent import followups, runner
from tutor_agent.followups import Turn
from tutor_agent.lessons import Lesson
from tutor_agent.settings import Settings
from tutor_agent.store import Concept, Source, Status

SOURCE = Source(snippet="for delay in (1, 2, 4):\n    ...", context="the agent wrapped a flaky call",
                project="/home/me/Projects/api", file="/home/me/Projects/api/client.py")
LESSON = Lesson("retry-with-backoff", "## What the agent did\nIt retries.", "sonnet", "t", SOURCE)


def concept(cid="retry-with-backoff", status=Status.SEEN, updated="2026-11-13T10:00:00+00:00", **kw) -> Concept:
    name = kw.pop("name", cid.replace("-", " ").capitalize())
    return Concept(id=cid, name=name, category="Design patterns", summary=f"About {name}.",
                   status=status, updated_at=updated, sources=[SOURCE], **kw)


def test_known_concepts_are_seen_or_understood_newest_first_without_the_lesson_itself():
    concepts = [
        concept("retry-with-backoff"),
        concept("idempotency", Status.UNDERSTOOD, "2026-11-13T09:00:00+00:00"),
        concept("circuit-breaker", Status.SEEN, "2026-11-13T11:00:00+00:00"),
        concept("jitter", Status.NEW),
        concept("bulkhead", Status.DISMISSED),
    ]
    known = followups.known_concepts(concepts, exclude="retry-with-backoff")
    assert [c.id for c in known] == ["circuit-breaker", "idempotency"]
    assert len(followups.known_concepts(concepts, limit=1)) == 1


def test_trim_thread_drops_oldest_turns_but_keeps_the_newest():
    thread = [Turn(f"q{i}", "a" * 100) for i in range(5)]
    kept, dropped = followups.trim_thread(thread, budget=250)
    assert [t.question for t in kept] == ["q3", "q4"] and dropped == 3
    huge = [Turn("old", "x"), Turn("new", "y" * 10_000)]
    assert followups.trim_thread(huge, budget=100) == ([huge[1]], 1)
    assert followups.trim_thread([]) == ([], 0)


def test_prompt_holds_lesson_snippet_known_thread_and_question():
    known = [concept("idempotency", Status.UNDERSTOOD, name="Idempotency")]
    thread = [Turn("Why 1, 2, 4?", "Exponential backoff.")]
    prompt = followups.build_prompt(concept(), LESSON, thread, known, "What about jitter?")
    assert "CONCEPT: Retry with backoff" in prompt
    assert "FILE: /home/me/Projects/api/client.py" in prompt
    assert "```\nfor delay in (1, 2, 4):\n    ...\n```" in prompt
    assert "## What the agent did\nIt retries." in prompt
    assert "- Idempotency [understood]: About Idempotency." in prompt
    assert "Q: Why 1, 2, 4?\nA: Exponential backoff." in prompt
    assert prompt.endswith("QUESTION:\nWhat about jitter?")


def test_prompt_marks_trimmed_thread_and_empty_knowledge():
    thread = [Turn("old " * 3000, "x"), Turn("new", "y")]
    prompt = followups.build_prompt(concept(), LESSON, thread, [], "q")
    assert "(none yet)" in prompt
    assert "[1 older follow-ups left out]" in prompt
    assert "old old" not in prompt


def test_answer_uses_the_lesson_model_without_tools_or_session(fake_claude):
    text = followups.answer(concept(), LESSON, [], [], "Why?", Settings(lesson_model="opus"))
    argv = fake_claude.record["argv"]
    assert argv[argv.index("--model") + 1] == "opus"
    assert "--no-session-persistence" in argv and "--resume" not in argv  # ADR 0012
    assert "follow-up question" in argv[argv.index("--system-prompt") + 1]
    assert text.startswith("echo: CONCEPT:") and text.endswith("QUESTION:\nWhy?")


def test_failed_answer_raises(fake_claude):
    fake_claude.mode("fail")
    with pytest.raises(runner.ClaudeError):
        followups.answer(concept(), LESSON, [], [], "Why?", Settings())
