"""Skip batches that can't teach anything, before any LLM call (docs/observation/triggers.md)."""

from tutor_agent.events import Event, Kind

# Total agent text in a turn with no edits and no commands. Below this it's a short answer or a
# status line; above it, the agent probably explained a design or a trade-off.
MIN_REASONING_CHARS = 600


def skip_reason(events: list[Event]) -> str | None:
    """Why the batch is not worth a detection call, or None if it is."""
    if not events:
        return "no new events"
    kinds = {e.kind for e in events}
    if Kind.EDIT in kinds or Kind.COMMAND in kinds:
        return None
    reasoning = sum(len(e.content) for e in events if e.kind is Kind.REASONING)
    if reasoning >= MIN_REASONING_CHARS:
        return None
    return f"no edits, no commands, only {reasoning} chars of reasoning"
