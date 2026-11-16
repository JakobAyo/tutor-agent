"""Spike Q7: cut chosen transcript turns into anonymized fixture batches.

Usage: python spike/make_fixtures.py NAME=TRANSCRIPT[:TURN] ...
  writes tests/fixtures/batches/NAME.json; without :TURN the whole transcript is one batch.
  The transcripts are private, so they are passed in and never named in the repo.
  Set TUTOR_REDACT (comma-separated words) to hide more names, e.g. projects or a company.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_events import anonymize, events, turns  # noqa: E402

out = Path(__file__).parent.parent / "tests/fixtures/batches"
out.mkdir(parents=True, exist_ok=True)
for arg in sys.argv[1:]:
    name, spec = arg.split("=", 1)
    path, _, idx = spec.partition(":")
    batch = [e for _, e in events(Path(path))] if not idx else list(turns(Path(path)))[int(idx)]
    batch = json.loads(anonymize(json.dumps(batch)))
    for e in batch:
        e["transcript_ref"] = f"<transcript>:{e['transcript_ref'].rsplit(':', 1)[1]}"
    (out / f"{name}.json").write_text(json.dumps(batch, indent=1))
    print(name, len(batch), "events", len(json.dumps(batch)) // 1000, "k chars")
