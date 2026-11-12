"""Spike Q7: cut chosen transcript turns into anonymized fixture batches.

Usage: python spike/make_fixtures.py   (writes tests/fixtures/batches/*.json)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_events import anonymize, events, turns  # noqa: E402

P = Path.home() / ".claude/projects"
CHOSEN = {  # name: (transcript, turn index or None for the whole file)
    "harness-gates-python": (P / "<transcript>.jsonl", 1),
    "ics-meeting-widget": (P / "<transcript>.jsonl", 1),
    "qml-animation-widget": (P / "<transcript>.jsonl", 0),
    "supervisor-loop": (P / "<transcript>.jsonl", 0),
    "subagent": (Path(sys.argv[1]) if len(sys.argv) > 1 else None, None),
}
out = Path(__file__).parent.parent / "tests/fixtures/batches"
out.mkdir(parents=True, exist_ok=True)
for name, (path, idx) in CHOSEN.items():
    if path is None:
        continue
    batch = [e for _, e in events(path)] if idx is None else list(turns(path))[idx]
    batch = json.loads(anonymize(json.dumps(batch)))
    for e in batch:
        e["transcript_ref"] = f"<transcript>:{e['transcript_ref'].rsplit(':', 1)[1]}"
    (out / f"{name}.json").write_text(json.dumps(batch, indent=1))
    print(name, len(batch), "events", len(json.dumps(batch)) // 1000, "k chars")
