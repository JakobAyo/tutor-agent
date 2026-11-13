"""Load the M0 fixture batches (anonymized event lists) as `Event`s."""

import json
from pathlib import Path

from tutor_agent.events import Event, Kind

DIR = Path(__file__).parent / "fixtures" / "batches"
NAMES = sorted(p.stem for p in DIR.glob("*.json"))


def load(name: str) -> list[Event]:
    return [Event(**{**e, "kind": Kind(e["kind"])}) for e in json.loads((DIR / f"{name}.json").read_text())]
