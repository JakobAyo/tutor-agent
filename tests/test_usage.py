import json

from tutor_agent import cli, paths, usage
from tutor_agent.store import ConceptStore, Source


def write(*records):
    paths.usage_file().write_text("".join(json.dumps(r) + "\n" for r in records) + "not json\n")


def rec(at, job="detect", cost=0.001, ok=True, ms=1000):
    return {"at": at, "job": job, "model": "haiku", "ms": ms, "cost_usd": cost, "ok": ok}


def test_per_day_sums_calls_cost_and_failures():
    write(rec("2026-11-12T10:00:00+00:00"), rec("2026-11-13T10:00:00+00:00", job="lesson", cost=0.015),
          rec("2026-11-13T11:00:00+00:00", cost=None, ok=False), rec("2026-11-13T12:00:00+00:00"))
    days = usage.per_day()
    assert list(days) == ["2026-11-12", "2026-11-13"]
    d = days["2026-11-13"]
    assert dict(d.calls) == {"lesson": 1, "detect": 2}
    assert d.failed == 1
    assert round(d.cost_usd, 4) == 0.016
    assert d.ms == 3000


def test_no_ledger_means_no_days():
    assert usage.per_day() == {}


def test_stats_prints_memory_and_usage(capsys):
    ConceptStore().add("Retry with backoff", "Design patterns", "s", Source(snippet="x", context="c"))
    write(rec("2026-11-13T10:00:00+00:00", job="lesson", cost=0.015))
    assert cli.main(["stats"]) == 0
    out = capsys.readouterr().out
    assert "1 concepts, 1 sources" in out
    assert "new: 1, seen: 0, understood: 0, dismissed: 0" in out
    assert "2026-11-13" in out and "lesson 1" in out and "$0.015" in out


def test_stats_without_data(capsys):
    assert cli.main(["stats"]) == 0
    assert "no calls recorded yet" in capsys.readouterr().out
