"""Lesson quality with the real lesson model (Sonnet by default). One call, so it only runs
with `-m prompt`. Checks the M4 "done when" item: the lesson quotes the real snippet, then
generalizes, covers trade-offs, and gives 2-3 links.
"""

import re
import shutil

import batches
import pytest

from tutor_agent import detector, lessons
from tutor_agent.settings import Settings
from tutor_agent.store import Concept, Source

pytestmark = [pytest.mark.prompt, pytest.mark.skipif(shutil.which("claude") is None, reason="claude not installed")]

SECTIONS = ("## What the agent did", "## Why it did it", "## The general concept", "## Trade-offs", "## Read more")


def test_lesson_has_the_structure_and_quotes_the_snippet():
    event = batches.load("supervisor-loop")[3]  # the edit of supervisor.py
    snippet = detector.snippet(event)
    concept = Concept(
        id="supervisor-with-last-known-good-rollback", name="Supervisor with last-known-good rollback",
        category="Design patterns",
        summary="A parent process restarts a child and falls back to the last version that worked.",
        sources=[Source(snippet=snippet, context="The agent wrote a loop that restarts the harness "
                        "and rolls back to the last good commit when the new one fails.",
                        project="~/Projects/project-d", file=event.file)],
    )
    text = lessons.generate(concept, Settings()).text

    positions = [text.find(s) for s in SECTIONS]
    assert all(p >= 0 for p in positions), f"missing sections in:\n{text}"
    assert positions == sorted(positions), "sections out of order"

    quoted = text[positions[0]:positions[1]]
    code_lines = {line.strip() for line in snippet.splitlines() if len(line.strip()) > 15}
    assert any(line in quoted for line in code_lines), "no line of the real snippet is quoted"

    links = re.findall(r"https?://\S+", text[positions[4]:])
    assert 2 <= len(links) <= 3, links
    assert len(text.split()) < 700
