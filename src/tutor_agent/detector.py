"""Find worth-knowing concepts in a batch with one `claude -p` call (ADR 0016, 0023, 0027).

The model returns names, summaries and an `event_index`. The snippet is cut from that event
here, never copied by the model (ADR 0013). The answer is validated item by item: a bad item is
logged and dropped, the rest is used.
"""

import json
from dataclasses import dataclass

from tutor_agent import runner
from tutor_agent.events import Event
from tutor_agent.log import get_logger
from tutor_agent.settings import Settings

# The concept categories from docs/pedagogy/curriculum.md. The pane groups concepts by these.
CATEGORIES = (
    "Design patterns",
    "Architecture and system design",
    "Language mechanisms",
    "Testing",
    "Tooling and build systems",
    "Infrastructure and deployment",
    "Concurrency and performance",
    "AI/LLM engineering",
)
MAX_CONCEPTS = 3
SNIPPET_LINES = 40

SCHEMA = {
    "type": "object",
    "properties": {
        "concepts": {
            "type": "array",
            "maxItems": MAX_CONCEPTS,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "category": {"type": "string", "enum": list(CATEGORIES)},
                    "summary": {"type": "string"},
                    "why_here": {"type": "string"},
                    "event_index": {"type": "integer"},
                    "reuses_known": {"type": "boolean"},
                },
                "required": ["name", "category", "summary", "why_here", "event_index", "reuses_known"],
            },
        }
    },
    "required": ["concepts"],
}

SYSTEM_PROMPT = f"""You find programming concepts worth learning in a coding agent's activity.
The learner has a CS degree but little practical experience. They want senior-level understanding.

Report a concept only if BOTH are true:
1. It is reusable understanding that helps read FUTURE code: design patterns, architecture,
   concurrency, testing strategies, tooling internals, infrastructure, language mechanisms,
   AI/LLM engineering, or a trade-off the agent made.
2. It actually shows up in the events (code written, a command run, or a decision the agent explained).

Never report: basic syntax (loops, conditionals, assignment), a single API call with no idea
behind it, renames, formatting, or facts about this one project.
Name concepts at a general level ("dependency injection", not "the get_db function").

KNOWN lists concepts the learner already has. If what you see is one of them, use the KNOWN
name exactly and set reuses_known to true; never rename or rephrase a known concept.
Otherwise set reuses_known to false.

Report at most {MAX_CONCEPTS} concepts, the most valuable first. Report none if nothing qualifies.
summary: one sentence on what the concept is.
why_here: one sentence on why the agent used it here.
event_index: the [index] of the event where the concept is IMPLEMENTED or USED, because the
learner's lesson quotes that event. In order of preference: an edit that writes the code, a
command that uses it, output that shows the code, and only if none of these shows it, the
reasoning where the agent explained the decision. An edit to the main code beats an edit to its
tests. Never pick a commit message or a summary of finished work if an earlier event shows the
code: those only mention the concept. Each concept should point at its own event."""


@dataclass(frozen=True)
class Candidate:
    """One concept the model found, with the event it points at."""

    name: str
    category: str
    summary: str
    why_here: str
    reuses_known: bool
    event: Event


class InvalidItem(ValueError):
    pass


def build_prompt(events: list[Event], known_names: list[str]) -> str:
    lines = [f"KNOWN: {json.dumps(sorted(known_names), ensure_ascii=False)}", "", "EVENTS:"]
    for i, e in enumerate(events):
        where = f" {e.file}" if e.file else ""
        lines.append(f"[{i}] {e.kind}{where}\n{e.content}")
    return "\n".join(lines)


def snippet(event: Event) -> str:
    """The event's content, cut to the first SNIPPET_LINES lines (ADR 0013)."""
    lines = event.content.splitlines()
    if len(lines) <= SNIPPET_LINES:
        return event.content
    return "\n".join(lines[:SNIPPET_LINES]) + f"\n[... {len(lines) - SNIPPET_LINES} more lines cut ...]"


def parse(structured, events: list[Event]) -> list[Candidate]:
    """Turn the structured output into candidates. Bad items are logged and dropped."""
    log = get_logger()
    if not isinstance(structured, dict) or not isinstance(structured.get("concepts"), list):
        log.error("detection output has no concepts list, dropped: %.500r", structured)
        return []
    out: list[Candidate] = []
    for raw in structured["concepts"][:MAX_CONCEPTS]:
        try:
            out.append(_candidate(raw, events))
        except InvalidItem as e:
            log.warning("dropped invalid concept %.300r: %s", raw, e)
    return out


def _candidate(raw, events: list[Event]) -> Candidate:
    if not isinstance(raw, dict):
        raise InvalidItem("not an object")
    texts = {}
    for key in ("name", "category", "summary", "why_here"):
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            raise InvalidItem(f"{key} missing or empty")
        texts[key] = " ".join(value.split())  # one line each
    if not any(c.isalnum() for c in texts["name"]):
        raise InvalidItem("name has no letters or digits")
    if texts["category"] not in CATEGORIES:
        raise InvalidItem(f"unknown category {texts['category']!r}")
    index = raw.get("event_index")
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(events):
        raise InvalidItem(f"event_index {index!r} out of range 0..{len(events) - 1}")
    reuses = raw.get("reuses_known")
    if not isinstance(reuses, bool):
        raise InvalidItem("reuses_known is not a boolean")
    return Candidate(reuses_known=reuses, event=events[index], **texts)


def detect(events: list[Event], known_names: list[str], settings: Settings) -> list[Candidate]:
    """One detection call on the cheap model. Raises `runner.ClaudeError` if the call fails."""
    result = runner.run(
        build_prompt(events, known_names),
        model=settings.detect_model,
        system_prompt=SYSTEM_PROMPT,
        json_schema=SCHEMA,
        timeout_s=settings.claude_timeout_s,
        claude_bin=settings.claude_bin,
        job="detect",
    )
    return parse(result.structured, events)
