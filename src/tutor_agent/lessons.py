"""Lessons: one `claude -p` call on the strong model per concept, cached on disk (ADR 0016, 0017, 0028).

A lesson starts from the stored snippet (ADR 0013), so it works after the transcript is gone.
The cache keeps the source it was built from, because follow-ups need it as context (ADR 0012).
"""

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from tutor_agent import paths, runner
from tutor_agent.settings import Settings
from tutor_agent.store import Concept, Source, now

SYSTEM_PROMPT = """You are a tutor. The learner watched a coding agent work and wants to understand
one concept behind what it did. They have a CS degree but little practical experience, and want
senior-level understanding. Skip basics. Be short and concrete: start from the code, not theory.

Write the lesson in Markdown with exactly these sections:

## What the agent did
Quote the relevant part of the snippet in a fenced code block (trim it to the lines that matter),
then say in one or two sentences what it does.

## Why it did it
The problem this concept solves here, in this project.

## The general concept
What it is beyond this case, in plain terms. Name the pattern or mechanism and where else it shows up.

## Trade-offs
When NOT to use it, what it costs, and the common alternatives.

## Read more
2-3 links as a Markdown list: official documentation, well-known articles or book chapters.
Only give URLs you are confident exist; prefer stable official docs over blog posts.

Keep the whole lesson under 500 words. Do not write code for the learner beyond the quoted snippet
and at most one short illustrative example."""


class LessonError(RuntimeError):
    pass


@dataclass(frozen=True)
class Lesson:
    concept_id: str
    text: str
    model: str
    generated_at: str
    source: Source  # what the lesson was built from; follow-ups reuse it (ADR 0012)

    @classmethod
    def from_dict(cls, raw: dict) -> "Lesson":
        return cls(**{**raw, "source": Source(**raw["source"])})


def lesson_source(concept: Concept) -> Source:
    """The most recent source (teaching strategy, ADR 0013)."""
    if not concept.sources:
        raise LessonError(f"concept {concept.id} has no source to teach from")
    return concept.sources[-1]


def fence(text: str) -> str:
    """A backtick fence longer than any run inside the text, so the snippet can't close it."""
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def build_prompt(concept: Concept, source: Source) -> str:
    f = fence(source.snippet)
    lines = [
        f"CONCEPT: {concept.name}",
        f"CATEGORY: {concept.category}",
        f"SUMMARY: {concept.summary}",
        "",
        f"PROJECT: {source.project or 'unknown'}",
    ]
    if source.file:
        lines.append(f"FILE: {source.file}")
    lines += [
        f"WHY IT CAME UP: {source.context}",
        "",
        "SNIPPET (what the agent wrote, ran or said):",
        f,
        source.snippet,
        f,
    ]
    return "\n".join(lines)


def generate(concept: Concept, settings: Settings) -> Lesson:
    """One call on the lesson model. Raises `runner.ClaudeError` or `LessonError`."""
    source = lesson_source(concept)
    result = runner.run(
        build_prompt(concept, source),
        model=settings.lesson_model,
        system_prompt=SYSTEM_PROMPT,
        timeout_s=settings.claude_timeout_s,
        claude_bin=settings.claude_bin,
    )
    text = result.text.strip()
    if not text:
        raise LessonError("the model returned an empty lesson")
    return Lesson(concept_id=concept.id, text=text, model=settings.lesson_model, generated_at=now(), source=source)


class LessonCache:
    """One JSON file per concept in `lessons/`. Written atomically; a broken file counts as missing."""

    def __init__(self, directory: Path | None = None) -> None:
        self.dir = directory or paths.lessons_dir()

    def path(self, cid: str) -> Path:
        return self.dir / f"{cid}.json"

    def get(self, cid: str) -> Lesson | None:
        try:
            return Lesson.from_dict(json.loads(self.path(cid).read_text(encoding="utf-8")))
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, TypeError, KeyError):
            return None  # regenerated on next open; the old file is replaced then

    def has(self, cid: str) -> bool:
        return self.get(cid) is not None

    def put(self, lesson: Lesson) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        target = self.path(lesson.concept_id)
        fd, tmp = tempfile.mkstemp(dir=self.dir, prefix=target.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(asdict(lesson), f, indent=1, ensure_ascii=False)
            os.replace(tmp, target)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
