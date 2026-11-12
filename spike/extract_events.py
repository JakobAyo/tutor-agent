"""Spike Q2: draft mapping from Claude Code transcript JSONL to tutor events.

Usage:
  python spike/extract_events.py <transcript.jsonl> [--from LINE] [--turns]
    prints events from LINE (0-based) on, as JSON lines
  --turns: print one summary line per turn instead (turn = starts at a real user prompt)

Throwaway code: the real reader is built in M2.
"""
import json
import re
import sys
from pathlib import Path

MAX_CONTENT = 2000  # chars per event; long outputs are cut in the middle
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
HOME = str(Path.home())


def truncate(text: str, limit: int = MAX_CONTENT) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return f"{text[:half]}\n[... {len(text) - limit} chars cut ...]\n{text[-half:]}"


def is_prompt(rec: dict) -> bool:
    """A real user prompt (not a tool result, not a meta/injected message)."""
    if rec.get("type") != "user" or rec.get("isMeta") or "toolUseResult" in rec:
        return False
    content = rec.get("message", {}).get("content")
    if isinstance(content, str):
        return not content.startswith(("<command-", "<local-command", "<task-notification"))
    return any(isinstance(b, dict) and b.get("type") == "text" for b in content or [])


def edit_content(name: str, inp: dict) -> str:
    if name == "Write":
        return inp.get("content", "")
    if name == "Edit":
        return f"--- old\n{inp.get('old_string', '')}\n+++ new\n{inp.get('new_string', '')}"
    if name == "MultiEdit":
        return "\n".join(f"--- old\n{e.get('old_string', '')}\n+++ new\n{e.get('new_string', '')}" for e in inp.get("edits", []))
    return json.dumps(inp)[:MAX_CONTENT]


def events(path: Path, start: int = 0):
    """Yield (line_no, event) for every relevant record at or after `start`."""
    bash_ids: set[str] = set()
    for no, line in enumerate(path.open(errors="replace")):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue  # a partly written last line: re-read it next time
        if rec.get("type") == "assistant":
            for b in rec["message"].get("content", []):
                if b.get("type") == "tool_use" and b["name"] == "Bash":
                    bash_ids.add(b["id"])
        if no < start or rec.get("type") not in ("user", "assistant"):
            continue
        base = {
            "session_id": rec.get("sessionId"),
            "project": rec.get("cwd"),
            "timestamp": rec.get("timestamp"),
            "agent_id": rec.get("agentId"),
            "transcript_ref": f"{path}:{no}",
        }
        msg = rec.get("message", {})
        if is_prompt(rec):
            c = msg["content"]
            text = c if isinstance(c, str) else "\n".join(b["text"] for b in c if b.get("type") == "text")
            yield no, {**base, "kind": "prompt", "file": None, "content": truncate(text)}
            continue
        for b in msg.get("content", []) if isinstance(msg.get("content"), list) else []:
            t = b.get("type")
            if t == "text" and rec["type"] == "assistant" and b["text"].strip():
                yield no, {**base, "kind": "reasoning", "file": None, "content": truncate(b["text"])}
            elif t == "thinking" and b.get("thinking", "").strip():
                yield no, {**base, "kind": "reasoning", "file": None, "content": truncate(b["thinking"])}
            elif t == "tool_use" and b["name"] in EDIT_TOOLS:
                inp = b["input"]
                yield no, {**base, "kind": "edit", "file": inp.get("file_path") or inp.get("notebook_path"),
                           "content": truncate(edit_content(b["name"], inp))}
            elif t == "tool_use" and b["name"] == "Bash":
                yield no, {**base, "kind": "command", "file": None,
                           "content": truncate(b["input"].get("command", ""))}
            elif t == "tool_result" and b.get("tool_use_id") in bash_ids:
                c = b.get("content")
                text = c if isinstance(c, str) else "\n".join(x.get("text", "") for x in c or [] if isinstance(x, dict))
                yield no, {**base, "kind": "tool_result", "file": None, "content": truncate(text, 800)}


def turns(path: Path):
    """Split events into turns. A turn starts at a real user prompt."""
    cur: list[dict] = []
    for _, ev in events(path):
        if ev["kind"] == "prompt" and cur:
            yield cur
            cur = []
        cur.append(ev)
    if cur:
        yield cur


def anonymize(text: str) -> str:
    text = text.replace(HOME, "~")
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", text)
    text = re.sub(r"(?i)\bexample-corp\b", "<company>", text)
    return re.sub(rf"(?i){re.escape(Path.home().name)}\w*", "<user>", text)


if __name__ == "__main__":
    p = Path(sys.argv[1])
    if "--turns" in sys.argv:
        for i, t in enumerate(turns(p)):
            kinds = {}
            for e in t:
                kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
            print(i, kinds, repr(t[0]["content"][:80]))
    else:
        start = int(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 0
        for _, ev in events(p, start):
            print(json.dumps(ev))
