"""Turn Claude Code transcript records into tutor events.

The mapping is described in docs/observation/event-model.md.

Pure functions, no file access: the reader feeds records in, in transcript order.
"""

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

MAX_CONTENT = 2000  # chars per event
MAX_TOOL_RESULT = 800  # command output is cut harder
EDIT_TOOLS = frozenset({"Edit", "MultiEdit", "Write", "NotebookEdit"})
# User records that Claude Code injects, not things I typed.
_WRAPPERS = ("<command-", "<local-command", "<task-notification", "<system-reminder")


class Kind(StrEnum):
    PROMPT = "prompt"
    REASONING = "reasoning"
    EDIT = "edit"
    COMMAND = "command"
    TOOL_RESULT = "tool_result"


@dataclass(frozen=True)
class Event:
    session_id: str
    agent_id: str | None
    project: str
    timestamp: str
    kind: Kind
    file: str | None
    content: str
    transcript_ref: str


def truncate(text: str, limit: int = MAX_CONTENT) -> str:
    """Keep whole lines from the start and the end, cut the middle. Good enough for reading."""
    if len(text) <= limit:
        return text
    half = limit // 2
    lines = text.splitlines(keepends=True)
    head = _fit(lines, half)
    tail = _fit(lines[len(head) :][::-1], half)[::-1]
    if not head and not tail:  # one giant line: fall back to a character cut
        return text[:half] + f"\n[... {len(text) - 2 * half} chars cut ...]\n" + text[-half:]
    cut = len(text) - sum(map(len, head)) - sum(map(len, tail))
    return "".join(head) + f"[... {cut} chars cut ...]\n" + "".join(tail)


def _fit(lines: list[str], budget: int) -> list[str]:
    """The longest prefix of `lines` whose total length fits in `budget`."""
    out: list[str] = []
    for line in lines:
        if len(line) > budget:
            break
        out.append(line)
        budget -= len(line)
    return out


def _hunk(old: str, new: str) -> str:
    return f"--- old\n{old}\n+++ new\n{new}"


def edit_content(tool: str, inp: dict[str, Any], limit: int = MAX_CONTENT) -> str:
    """An edit as text, cut so that whole hunks survive (M0 lost half a function to a middle cut).

    Order of sacrifice: old sides first (the new code is what the lesson explains), then whole
    trailing hunks, and only a single oversized hunk is cut, keeping its first lines.
    """
    if tool == "Write":
        return _head_lines(inp.get("content", ""), limit)
    if tool == "NotebookEdit":
        return _head_lines(inp.get("new_source", ""), limit)
    if tool == "Edit":
        pairs = [(inp.get("old_string", ""), inp.get("new_string", ""))]
    else:  # MultiEdit
        pairs = [(e.get("old_string", ""), e.get("new_string", "")) for e in inp.get("edits", [])]

    full = "\n".join(_hunk(o, n) for o, n in pairs)
    if len(full) <= limit:
        return full
    hunks = [f"+++ new\n{n}" for _, n in pairs]
    kept: list[str] = []
    used = 0
    for h in hunks:
        if used + len(h) + 1 > limit:
            break
        kept.append(h)
        used += len(h) + 1
    if not kept:
        return _head_lines(hunks[0], limit) + _dropped(len(hunks) - 1)
    return "[old side omitted]\n" + "\n".join(kept) + _dropped(len(hunks) - len(kept))


def _dropped(n: int) -> str:
    return f"\n[... {n} more hunks cut ...]" if n else ""


def _head_lines(text: str, limit: int) -> str:
    """Keep whole lines from the start: a file's top (imports, signatures) explains the most."""
    if len(text) <= limit:
        return text
    kept = "".join(_fit(text.splitlines(keepends=True), limit)) or text[:limit]
    return kept + f"\n[... {len(text) - len(kept)} chars cut ...]"


def is_prompt(rec: dict[str, Any]) -> bool:
    """A real user prompt: not a tool result, not meta, not a wrapper Claude Code injected."""
    if rec.get("type") != "user" or not isinstance(rec.get("message"), dict):
        return False
    if rec.get("isMeta") or "toolUseResult" in rec:
        return False
    content = rec["message"].get("content")
    if isinstance(content, str):
        return bool(content.strip()) and not content.lstrip().startswith(_WRAPPERS)
    return any(isinstance(b, dict) and b.get("type") == "text" for b in content or [])


def text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(
        b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text"
    )


class EventMapper:
    """Maps records one at a time. Stateful only to know which tool results belong to `Bash`."""

    def __init__(self) -> None:
        self._bash_ids: set[str] = set()

    def map(self, rec: dict[str, Any], ref: str) -> list[Event]:
        rtype = rec.get("type")
        if rtype not in ("user", "assistant"):
            return []  # unknown and metadata record types are ignored, never an error
        msg = rec.get("message")
        if not isinstance(msg, dict):
            return []

        def ev(kind: Kind, content: str, file: str | None = None) -> Event:
            return Event(
                session_id=rec.get("sessionId", ""),
                agent_id=rec.get("agentId"),
                project=rec.get("cwd", ""),
                timestamp=rec.get("timestamp", ""),
                kind=kind,
                file=file,
                content=content,
                transcript_ref=ref,
            )

        if rtype == "user" and is_prompt(rec):
            return [ev(Kind.PROMPT, truncate(text_of(msg.get("content"))))]

        blocks = msg.get("content")
        if not isinstance(blocks, list):
            return []
        out: list[Event] = []
        for b in blocks:
            if not isinstance(b, dict):
                continue
            t = b.get("type")
            if rtype == "assistant" and t == "text" and b.get("text", "").strip():
                out.append(ev(Kind.REASONING, truncate(b["text"])))
            elif rtype == "assistant" and t == "thinking" and b.get("thinking", "").strip():
                out.append(ev(Kind.REASONING, truncate(b["thinking"])))
            elif t == "tool_use" and b.get("name") in EDIT_TOOLS:
                inp = b.get("input") or {}
                path = inp.get("file_path") or inp.get("notebook_path")
                out.append(ev(Kind.EDIT, edit_content(b["name"], inp), file=path))
            elif t == "tool_use" and b.get("name") == "Bash":
                self._bash_ids.add(b.get("id", ""))
                out.append(ev(Kind.COMMAND, truncate((b.get("input") or {}).get("command", ""))))
            elif t == "tool_result" and b.get("tool_use_id") in self._bash_ids:
                out.append(
                    ev(Kind.TOOL_RESULT, truncate(text_of(b.get("content")), MAX_TOOL_RESULT))
                )
        return out


def to_json(events: list[Event]) -> str:
    return json.dumps([e.__dict__ for e in events], ensure_ascii=False, indent=1)
