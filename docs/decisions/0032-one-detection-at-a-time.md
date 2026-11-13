# 0032: One detection at a time

- **Status:** Accepted
- **Date:** 2026-11-13

## Context
Each hook starts its own detached `tutor detect`. The reader's per-session lock ([0025](0025-byte-offsets-per-session.md)) is released before the slow `claude -p` call, so two detections can run at once. In real use (M6 log, 2026-11-13) two calls on the same session overlapped by about one second: the second read the KNOWN list before the first had stored its three concepts, and created "Append-only usage ledger for LLM calls" next to "Lock-free append-only log with O_APPEND", and "Golden-set regression tests for LLM prompts" next to "Testing non-deterministic LLM output…". The KNOWN-name rule ([0027](0027-detection-rules.md)) can only prevent near-duplicates when KNOWN is up to date.

## Decision
- **A global lock, `detect.lock`** in the data directory, held with `flock` from reading KNOWN through the detection call and the store transaction to the notification. Other detections wait for it.
- The read of the batch and the pre-filter stay outside the lock, so skipped batches never wait.

## Alternatives considered
- Re-check KNOWN after the call and drop names created meanwhile: only exact names can be matched in code, and the duplicates here had different names.
- A queue or daemon that runs detections in order: a long-running process to manage, for the same effect.
- Accept the duplicates and let the user dismiss them: they cost notifications, which the M6 goal says should not feel noisy.

## Consequences
- Bursts (many subagents finishing together) are handled one after another. Each waiting process is detached, so the agent session never notices. A hung call holds the others back by at most `claude_timeout_s`.
- The total usage is unchanged; only the order changes.
- Updated: [architecture/data-storage.md](../architecture/data-storage.md), [architecture/components.md](../architecture/components.md), [milestones/m6-daily-use.md](../milestones/m6-daily-use.md).
