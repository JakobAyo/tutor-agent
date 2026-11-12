"""Build Claude Code transcript records in the shape seen in M0 (Claude Code 2.1.322)."""

import json
from pathlib import Path

SESSION = "11111111-2222-3333-4444-555555555555"


def _base(rtype: str, agent_id: str | None = None, **extra) -> dict:
    rec = {
        "type": rtype,
        "sessionId": SESSION,
        "cwd": "/home/u/proj",
        "timestamp": "2026-11-12T10:00:00.000Z",
        "isSidechain": agent_id is not None,
        **extra,
    }
    if agent_id:
        rec["agentId"] = agent_id
    return rec


def prompt(text: str, **kw) -> dict:
    return _base("user", message={"role": "user", "content": text}, **kw)


def assistant(*blocks: dict, **kw) -> dict:
    return _base("assistant", message={"role": "assistant", "content": list(blocks)}, **kw)


def text(t: str) -> dict:
    return {"type": "text", "text": t}


def thinking(t: str) -> dict:
    return {"type": "thinking", "thinking": t, "signature": "x"}


def tool_use(tid: str, name: str, **inp) -> dict:
    return {"type": "tool_use", "id": tid, "name": name, "input": inp}


def tool_result(tid: str, content: str, **kw) -> dict:
    return _base(
        "user",
        message={"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "content": content}]},
        toolUseResult={"stdout": content},
        **kw,
    )


def other(rtype: str = "attachment") -> dict:
    return _base(rtype, attachment={"type": "whatever"})


def turn(n: int = 0, **kw) -> list[dict]:
    """One realistic agent turn: prompt, reasoning, an edit, a command and its output."""
    return [
        prompt(f"add caching #{n}", **kw),
        other(),
        assistant(thinking(""), text("I'll use an LRU cache."), **kw),
        assistant(tool_use(f"e{n}", "Edit", file_path="/home/u/proj/a.py", old_string="x", new_string="y"), **kw),
        tool_result(f"e{n}", "ok", **kw),
        assistant(tool_use(f"b{n}", "Bash", command="pytest -q"), **kw),
        tool_result(f"b{n}", "3 passed", **kw),
        assistant(text("Done."), **kw),
    ]


def write(path: Path, records: list[dict], *, append: bool = False, partial: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a" if append else "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
        f.write(partial)
    return path
