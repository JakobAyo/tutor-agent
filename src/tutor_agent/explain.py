""" "What just happened": explain a session's latest turn on demand (F8, ADR 0029).

Read-only on transcripts and independent of detection: it never moves an offset. The latest
turn starts at the last real prompt in the main transcript and includes the work of subagents
that wrote records after that prompt.
"""

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tutor_agent import paths, runner
from tutor_agent.events import Event, EventMapper, Kind, is_prompt, text_of
from tutor_agent.followups import known_lines
from tutor_agent.settings import Settings
from tutor_agent.store import Concept

RECENT_SESSIONS = 10
TAIL_BYTES = 256 * 1024  # first read of a transcript's end to label it in the session picker
MAX_TAIL_BYTES = 8 * 1024 * 1024
TURN_BUDGET = 40_000  # chars of event content per explanation; the oldest work goes first
MAX_TURN_EVENTS = 150

SYSTEM_PROMPT = """You are a tutor. The learner just watched a coding agent work and asks:
"what just happened, and why?" They have a CS degree but little practical experience, and want
senior-level understanding. Skip basics. Start from the code, not theory.

The events are one turn: the learner's prompt, then the agent's reasoning, edits, commands and
their output, in order. Events marked with an agent id come from subagents the agent started.

Write Markdown with exactly these sections:

## What happened
The steps the agent took, in order, in a few bullets. Quote the lines of code or the commands
that matter (short fenced blocks), and say what each step achieved.

## Why it did it this way
The decisions behind the steps: what problem each one solved, which alternatives it passed over,
and what it costs. Say so if the reason is not visible in the events instead of guessing.

## Concepts behind it
2-4 concepts worth knowing, one line each. For concepts in KNOWS, just name them; explain only
the new ones.

## Worth checking
Up to 3 things a senior engineer would review or question in this work. Leave the section out if
there is nothing real.

Keep it under 500 words. Explain; don't write code for the learner."""


class ExplainError(RuntimeError):
    pass


@dataclass(frozen=True)
class Session:
    session_id: str
    transcript: Path
    last_active: float  # mtime of the newest of its transcript files
    project: str | None = None
    last_prompt: str | None = None

    def label(self, now: float | None = None) -> str:
        project = self.project.rstrip("/").rsplit("/", 1)[-1] if self.project else "?"
        prompt = " ".join((self.last_prompt or "(no prompt found)").split())
        if len(prompt) > 70:
            prompt = prompt[:69] + "…"
        return f"{project} · {ago((now or time.time()) - self.last_active)}\n  {prompt}"


@dataclass
class LatestTurn:
    session: Session
    events: list[Event] = field(default_factory=list)
    dropped_events: int = 0  # older work left out by the budget
    subagent_events: int = 0


def ago(seconds: float) -> str:
    seconds = max(0, int(seconds))
    for unit, size in (("d", 86400), ("h", 3600), ("min", 60)):
        if seconds >= size:
            return f"{seconds // size} {unit} ago"
    return "just now"


def subagent_transcripts(transcript: Path) -> list[Path]:
    return sorted((transcript.parent / transcript.stem / "subagents").glob("agent-*.jsonl"))


def _records(path: Path, start: int = 0) -> Iterator[dict[str, Any]]:
    """Parsed dict records from `start` on. Broken and partial lines are skipped."""
    with path.open("rb") as f:
        f.seek(start)
        if start:
            f.readline()  # most likely the middle of a line
        for raw in f:
            if not raw.endswith(b"\n"):
                break
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                yield rec


def describe(transcript: Path, last_active: float) -> Session:
    """Label a session from the end of its transcript: the project and the last prompt.

    Long turns push the prompt far back, so the tail grows until a prompt shows up.
    """
    size = transcript.stat().st_size
    project = prompt = None
    tail = TAIL_BYTES
    while True:
        for rec in _records(transcript, max(0, size - tail)):
            project = rec.get("cwd") or project
            if is_prompt(rec):
                prompt = text_of(rec["message"].get("content")).strip() or prompt
        if prompt or tail >= min(size, MAX_TAIL_BYTES):
            return Session(transcript.stem, transcript, last_active, project, prompt)
        tail *= 4


def recent_sessions(
    limit: int = RECENT_SESSIONS, projects_dir: Path | None = None
) -> list[Session]:
    """The most recently active main sessions, newest first. Subagent activity counts too."""
    projects_dir = projects_dir or paths.claude_projects_dir()
    found: list[tuple[float, Path]] = []
    for transcript in projects_dir.glob("*/*.jsonl"):
        try:
            mtime = max(p.stat().st_mtime for p in [transcript, *subagent_transcripts(transcript)])
        except FileNotFoundError:  # cleaned up while we looked
            continue
        found.append((mtime, transcript))
    found.sort(reverse=True)
    sessions = []
    for mtime, transcript in found[:limit]:
        try:
            sessions.append(describe(transcript, mtime))
        except OSError:
            continue
    return sessions


def latest_turn(session: Session) -> LatestTurn:
    """Events from the last prompt to the end, merged with subagent work from the same span."""
    turn_records: list[tuple[dict[str, Any], str]] = []
    start_ts = ""
    for line, rec in enumerate(_records(session.transcript), 1):
        if is_prompt(rec):
            turn_records = []
            start_ts = rec.get("timestamp", "")
        turn_records.append((rec, f"{session.transcript}:{line}"))

    mapper = EventMapper()
    events = [e for rec, ref in turn_records for e in mapper.map(rec, ref)]
    sub_events: list[Event] = []
    for path in subagent_transcripts(session.transcript):
        sub_mapper = EventMapper()  # tool ids are per transcript
        for line, rec in enumerate(_records(path), 1):
            if rec.get("timestamp", "") >= start_ts:
                sub_events.extend(sub_mapper.map(rec, f"{path}:{line}"))
    # Stable sort: main events keep their order, subagent events slot in by time.
    merged = sorted(events + sub_events, key=lambda e: e.timestamp)
    kept, dropped = fit(merged)
    return LatestTurn(session, kept, dropped, sum(e.agent_id is not None for e in kept))


def fit(
    events: list[Event], budget: int = TURN_BUDGET, max_events: int = MAX_TURN_EVENTS
) -> tuple[list[Event], int]:
    """Keep the prompt and the newest events that fit. Returns them and how many were dropped."""
    head = [e for e in events[:1] if e.kind is Kind.PROMPT]
    used = sum(len(e.content) for e in head)
    tail: list[Event] = []
    for e in reversed(events[len(head) :]):
        if len(head) + len(tail) >= max_events or (tail and used + len(e.content) > budget):
            break
        tail.append(e)
        used += len(e.content)
    tail.reverse()
    return head + tail, len(events) - len(head) - len(tail)


def build_prompt(turn: LatestTurn, known: list[Concept]) -> str:
    s = turn.session
    lines = [
        f"PROJECT: {s.project or 'unknown'}",
        "",
        "KNOWS (concepts the learner has seen or understood):",
        *known_lines(known),
        "",
        "EVENTS:",
    ]
    if turn.dropped_events:
        lines.append(f"[{turn.dropped_events} earlier events of this turn left out]")
    for e in turn.events:
        who = f" (subagent {e.agent_id})" if e.agent_id else ""
        where = f" {e.file}" if e.file else ""
        lines.append(f"- {e.kind}{who}{where}\n{e.content}")
    return "\n".join(lines)


def explain(turn: LatestTurn, known: list[Concept], settings: Settings) -> str:
    """One call on the lesson model. Raises `runner.ClaudeError` or `ExplainError`."""
    if not any(e.kind is not Kind.PROMPT for e in turn.events):
        raise ExplainError("the latest turn has no agent activity yet")
    result = runner.run(
        build_prompt(turn, known),
        model=settings.lesson_model,
        system_prompt=SYSTEM_PROMPT,
        timeout_s=settings.claude_timeout_s,
        claude_bin=settings.claude_bin,
        job="explain",
    )
    text = result.text.strip()
    if not text:
        raise ExplainError("the model returned an empty explanation")
    return text
