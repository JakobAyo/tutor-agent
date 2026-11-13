"""Follow-up questions on a lesson: one fresh `claude -p` call per question (ADR 0012, 0029).

Nothing is resumed. Every prompt is rebuilt from the lesson (text and the source it quoted), the
thread so far, the concepts I already know, and the new question. Long threads lose their
oldest turns first, so the prompt stays bounded.
"""

from dataclasses import dataclass

from tutor_agent import runner
from tutor_agent.lessons import Lesson, fence
from tutor_agent.settings import Settings
from tutor_agent.store import Concept, Status

SYSTEM_PROMPT = """You are a tutor. The learner read a lesson about one concept, built from code a
coding agent wrote, and now asks a follow-up question. They have a CS degree but little practical
experience, and want senior-level understanding. Skip basics.

Answer the QUESTION in the context of the LESSON and its SNIPPET. Refer back to that code when it
helps. Build on what the learner already KNOWS: name those concepts instead of explaining them
again. Use the THREAD so far, and don't repeat earlier answers.

Be short: usually under 250 words, in Markdown. Explain, don't write code for the learner; at most
one short illustrative example. If the question is outside the lesson's topic, answer briefly and
say how it connects. Only give links you are confident exist."""

MAX_KNOWN = 40  # known concepts listed in the prompt, most recently touched first
THREAD_BUDGET = 12_000  # chars of earlier Q&A kept in the prompt; the oldest turns go first


@dataclass(frozen=True)
class Turn:
    question: str
    answer: str


def known_concepts(concepts: list[Concept], exclude: str | None = None, limit: int = MAX_KNOWN) -> list[Concept]:
    """What I already know: `seen` and `understood` concepts, most recently touched first."""
    known = [c for c in concepts if c.status in (Status.SEEN, Status.UNDERSTOOD) and c.id != exclude]
    known.sort(key=lambda c: c.updated_at, reverse=True)
    return known[:limit]


def known_lines(known: list[Concept]) -> list[str]:
    if not known:
        return ["(none yet)"]
    return [f"- {c.name} [{c.status}]: {c.summary}" for c in known]


def trim_thread(thread: list[Turn], budget: int = THREAD_BUDGET) -> tuple[list[Turn], int]:
    """The newest turns that fit in `budget` chars, and how many older turns were dropped.

    The newest turn is always kept, even when it alone is over budget: the question that follows
    usually refers to it.
    """
    kept: list[Turn] = []
    used = 0
    for turn in reversed(thread):
        size = len(turn.question) + len(turn.answer)
        if kept and used + size > budget:
            break
        kept.append(turn)
        used += size
    kept.reverse()
    return kept, len(thread) - len(kept)


def build_prompt(concept: Concept, lesson: Lesson, thread: list[Turn], known: list[Concept], question: str) -> str:
    source = lesson.source
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
        f, source.snippet, f,
        "",
        "LESSON (what the learner just read):",
        lesson.text,
        "",
        "KNOWS (concepts the learner has seen or understood):",
        *known_lines(known),
        "",
    ]
    kept, dropped = trim_thread(thread)
    if kept:
        lines.append("THREAD (earlier follow-ups, oldest first):")
        if dropped:
            lines.append(f"[{dropped} older follow-ups left out]")
        for t in kept:
            lines += [f"Q: {t.question}", f"A: {t.answer}", ""]
    lines += ["QUESTION:", question]
    return "\n".join(lines)


class FollowUpError(RuntimeError):
    pass


def answer(concept: Concept, lesson: Lesson, thread: list[Turn], known: list[Concept], question: str,
           settings: Settings) -> str:
    """One call on the lesson model (ADR 0016). Raises `runner.ClaudeError` or `FollowUpError`."""
    result = runner.run(
        build_prompt(concept, lesson, thread, known, question),
        model=settings.lesson_model,
        system_prompt=SYSTEM_PROMPT,
        timeout_s=settings.claude_timeout_s,
        claude_bin=settings.claude_bin,
        job="followup",
    )
    text = result.text.strip()
    if not text:
        raise FollowUpError("the model returned an empty answer")
    return text
