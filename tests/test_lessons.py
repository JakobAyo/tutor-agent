import json

import pytest

from tutor_agent import lessons, runner
from tutor_agent.settings import Settings
from tutor_agent.store import Concept, Source

SNIPPET = 'def retry(fn):\n    """```inner fence```"""\n    for delay in (1, 2, 4):\n        ...'


def concept(**kw) -> Concept:
    old = Source(snippet="old = 1", context="first time", project="/home/me/Projects/old")
    new = Source(snippet=SNIPPET, context="the agent wrapped a flaky call", project="/home/me/Projects/api",
                 file="/home/me/Projects/api/client.py")
    base = dict(id="retry-with-backoff", name="Retry with backoff", category="Design patterns",
                summary="Retry a failing call with growing delays.", sources=[old, new])
    return Concept(**{**base, **kw})


def test_prompt_uses_most_recent_source_and_a_safe_fence():
    c = concept()
    prompt = lessons.build_prompt(c, lessons.lesson_source(c))
    assert "CONCEPT: Retry with backoff" in prompt
    assert "FILE: /home/me/Projects/api/client.py" in prompt
    assert "WHY IT CAME UP: the agent wrapped a flaky call" in prompt
    assert f"````\n{SNIPPET}\n````" in prompt  # 4 backticks: the snippet holds a 3-backtick run
    assert "old = 1" not in prompt


def test_lesson_prefers_code_over_a_newer_prose_source():
    """ADR 0030: a commit message or summary seen later must not replace the code snippet."""
    code = Source(snippet="def f(): ...", context="c", kind="edit", file="/p/a.py")
    cmd = Source(snippet="git commit -m 'add f'", context="c", kind="command")
    prose = Source(snippet="I added f.", context="c", kind="reasoning")
    assert lessons.lesson_source(concept(sources=[code, cmd, prose])) is code
    assert lessons.lesson_source(concept(sources=[prose, cmd])) is cmd
    newer_code = Source(snippet="def g(): ...", context="c", kind="edit")
    assert lessons.lesson_source(concept(sources=[code, prose, newer_code])) is newer_code


def test_old_sources_without_kind_rank_by_file():
    old_edit = Source(snippet="x = 1", context="c", file="/p/a.py")
    old_prose = Source(snippet="Done.", context="c")
    assert lessons.lesson_source(concept(sources=[old_edit, old_prose])) is old_edit
    assert lessons.lesson_source(concept(sources=[old_prose])) is old_prose


def test_concept_without_source_cannot_be_taught():
    with pytest.raises(lessons.LessonError):
        lessons.lesson_source(concept(sources=[]))


def test_generate_uses_the_lesson_model(fake_claude):
    lesson = lessons.generate(concept(), Settings(lesson_model="opus"))
    argv = fake_claude.record["argv"]
    assert argv[argv.index("--model") + 1] == "opus"
    assert "--json-schema" not in argv
    assert "## What the agent did" in argv[argv.index("--system-prompt") + 1]
    assert lesson.text.startswith("echo: CONCEPT: Retry with backoff")
    assert lesson.model == "opus"
    assert lesson.source.snippet == SNIPPET


def test_failed_call_raises(fake_claude):
    fake_claude.mode("fail")
    with pytest.raises(runner.ClaudeError):
        lessons.generate(concept(), Settings())


def test_cache_round_trip_and_atomic_write(data_dir):
    cache = lessons.LessonCache()
    assert cache.get("retry-with-backoff") is None
    lesson = lessons.Lesson("retry-with-backoff", "## What the agent did\n...", "sonnet", "t",
                            lessons.lesson_source(concept()))
    cache.put(lesson)
    assert cache.get("retry-with-backoff") == lesson
    assert [p.name for p in (data_dir / "lessons").iterdir()] == ["retry-with-backoff.json"]


def test_broken_cache_file_counts_as_missing(data_dir):
    cache = lessons.LessonCache()
    cache.dir.mkdir(parents=True)
    cache.path("x").write_text("{not json")
    assert cache.get("x") is None
    cache.path("y").write_text(json.dumps({"concept_id": "y"}))
    assert cache.get("y") is None
