"""Spike Q7/Q8: run a draft detection prompt on a fixture batch with a given model.

Usage: python spike/detect.py <batch.json> <model> <out.json>
Writes {model, batch, ms, cost_usd, input_tokens, output_tokens, concepts}.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

KNOWN = ["dependency injection", "secrets in environment variables", "atomic file writes"]

SCHEMA = {
    "type": "object",
    "properties": {
        "concepts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "category": {"type": "string", "enum": [
                        "pattern", "architecture", "mechanism", "trade-off", "tooling", "testing", "infra", "language"]},
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

SYSTEM = """You find programming concepts worth learning in a coding agent's activity.
The learner has a CS degree but little practical experience. They want senior-level understanding.

Report a concept only if BOTH are true:
1. It is reusable understanding that helps read FUTURE code: design patterns, architecture,
   concurrency, testing strategies, tooling internals, infra concepts, language mechanisms, trade-offs.
2. It actually shows up in the events (code written, a command run, or a decision the agent explained).

Never report: basic syntax, a single API call with no idea behind it, renames, formatting,
project-specific facts, or anything in the KNOWN list. If a concept matches a KNOWN name,
skip it. Name concepts at a general level ("dependency injection", not "the get_db function").
Report at most 3 concepts, the most valuable first. Report none if nothing qualifies.
summary: one sentence on what the concept is. why_here: one sentence on why the agent used it here.
event_index: index of the event that shows it best."""


def build_prompt(batch: list[dict]) -> str:
    lines = [f"KNOWN: {json.dumps(KNOWN)}", "", "EVENTS:"]
    for i, e in enumerate(batch):
        where = f" {e['file']}" if e.get("file") else ""
        lines.append(f"[{i}] {e['kind']}{where}\n{e['content']}")
    return "\n".join(lines)


def main() -> None:
    batch_path, model, out_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    batch = json.loads(batch_path.read_text())
    data_dir = Path.home() / ".local/share/tutor-agent-spike"
    data_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["claude", "-p", "--model", model, "--output-format", "json", "--tools", "",
           "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence",
           "--system-prompt", SYSTEM, "--json-schema", json.dumps(SCHEMA)]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, input=build_prompt(batch), capture_output=True, text=True, cwd=data_dir,
                       env={**os.environ, "TUTOR_AGENT_INTERNAL": "1"})
    ms = round((time.perf_counter() - t0) * 1000)
    d = json.loads(p.stdout)
    u = d.get("usage", {})
    concepts = d.get("structured_output") or d.get("result")
    out = {"model": model, "batch": batch_path.stem, "ms": ms, "cost_usd": d.get("total_cost_usd"),
           "input_tokens": u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0),
           "output_tokens": u.get("output_tokens"), "is_error": d.get("is_error"), "concepts": concepts}
    out_path.write_text(json.dumps(out, indent=1))
    print(batch_path.stem, model, ms, "ms")


if __name__ == "__main__":
    main()
