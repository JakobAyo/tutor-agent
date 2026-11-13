"""The usage ledger: one JSON line per `claude -p` call, so usage per day can be checked (ADR 0031).

Appending one short line with `O_APPEND` needs no lock: the kernel puts each write at the end, and
the detector, pane and `tutor explain` can append at the same time. The ledger is never needed for
the tutor to work, so a failed write is logged and ignored.
"""

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from tutor_agent import paths
from tutor_agent.log import get_logger
from tutor_agent.store import now


def record(job: str, model: str, duration_ms: int, cost_usd: float | None, *, ok: bool) -> None:
    line = json.dumps({"at": now(), "job": job, "model": model, "ms": duration_ms,
                       "cost_usd": cost_usd, "ok": ok}) + "\n"
    try:
        fd = os.open(paths.usage_file(), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, line.encode())
        finally:
            os.close(fd)
    except OSError as e:
        get_logger().warning("cannot write usage ledger: %s", e)


@dataclass
class Day:
    calls: dict[str, int] = field(default_factory=lambda: defaultdict(int))  # per job
    failed: int = 0
    cost_usd: float = 0.0
    ms: int = 0


def per_day() -> dict[str, Day]:
    """Usage per local calendar day, oldest first. Unreadable lines are skipped."""
    days: dict[str, Day] = defaultdict(Day)
    try:
        lines = paths.usage_file().read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return {}
    for line in lines:
        try:
            rec = json.loads(line)
            day = days[datetime.fromisoformat(rec["at"]).astimezone().date().isoformat()]
            day.calls[str(rec["job"])] += 1
            day.failed += not rec.get("ok", True)
            day.cost_usd += float(rec.get("cost_usd") or 0)
            day.ms += int(rec.get("ms") or 0)
        except (ValueError, KeyError, TypeError):
            continue
    return dict(sorted(days.items()))
