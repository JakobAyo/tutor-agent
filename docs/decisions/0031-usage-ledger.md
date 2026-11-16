# 0031: Usage ledger and `tutor stats`

- **Status:** Accepted
- **Date:** 2026-11-13

## Context
M6 has to check the size of the concept memory and the usage per day. The runner logs each call's cost in `tutor.log`, but the log rotates at 1 MB with two backups and mixes in everything else, so two weeks of usage can't be read back reliably. Failed and timed-out calls also use quota and were not counted with a cost line at all.

## Decision
- **`usage.jsonl`** in the data directory: one JSON line per `claude -p` call that the runner started, written by the runner: time, job (`detect`, `lesson`, `followup`, `explain`), model, duration, `total_cost_usd` (null if unknown), and `ok`. Failed calls and timeouts are recorded with `ok: false`.
- **Append without a lock:** each line is one `write` on a file opened with `O_APPEND`, so the detector, pane and `tutor explain` can append at the same time. Mode `600`.
- **Never in the way:** a failed ledger write is logged as a warning, and the call goes on. Unreadable lines are skipped when reading.
- **`tutor stats`** (no model call): concepts per status, number of sources, size of `concepts.json`, cached lessons, and per local day the calls per job, failures, cost and time (last 14 days with calls, `--days N`).
- No rotation. At about 150 bytes a line, even 200 calls a day is about 1 MB a month.

## Alternatives considered
- Parse `tutor.log`: rotates away, and the cost line has no job name.
- Keep counters in `concepts.json`: every call, including lessons from the pane, would take the store lock just to count.
- Read Claude Code's own usage data: not separated from my normal sessions, and the tutor runs without session persistence.

## Consequences
- The cost is what `claude -p` reports. On a subscription it is a list-price estimate, useful for comparing days and jobs, not a bill.
- Updated: [architecture/components.md](../architecture/components.md), [architecture/data-storage.md](../architecture/data-storage.md), [milestones/m6-daily-use.md](../milestones/m6-daily-use.md), `CLAUDE.md`.
