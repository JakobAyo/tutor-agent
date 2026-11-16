# 0025: Transcript offsets are byte positions in one file per session

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
[0015](0015-include-subagent-activity.md) asks for a read offset per session and per subagent transcript, and M2 asks for a per-session lock so two close hooks don't read the same lines twice. Open points: what an offset is, where it lives, what the lock covers, and what happens to a backlog, for example when the tutor is installed in the middle of a long session.

## Decision
- An offset is `{"byte": N, "line": L}`: the reader `seek`s to the byte position and counts lines for `transcript_ref` (1-based).
- Offsets live in `offsets/<session_id>.json` in the data directory, keyed by the resolved transcript path, with main and subagent transcripts in the same file. Writes use a temp file plus `os.replace`.
- An exclusive `flock` on `offsets/<session_id>.lock` covers *read offset → read lines → save offset*. The slow detection call runs after the lock is released.
- A line without a trailing newline is still being written: the reader stops before it. A complete line that is not valid JSON is skipped and logged, so the reader can't get stuck on it.
- A transcript smaller than its offset is read from the start again.
- A batch keeps at most the newest 150 events (`reader.MAX_EVENTS`). More than that is a backlog, not one turn.

## Alternatives considered
- Line numbers only: each read would scan the whole transcript, and transcripts reach several MB.
- One offsets file for all sessions: every hook in every session would wait on one lock.
- Lock around detection too: one slow call would block the next trigger of the same session for 10+ s, for no gain.
- Stop at an invalid JSON line, as the M0 draft did: a single corrupt line would stop detection for that session forever.

## Consequences
- Each line is read by exactly one batch, also with concurrent hooks (`tests/test_reader.py`; the test fails with the lock removed).
- If detection fails after the offset was saved, that batch is lost. That is accepted: re-running a failed call could double the usage.
- One small file per session piles up in `offsets/`. Clean-up can come later if it matters.
- Updated: [architecture/data-storage.md](../architecture/data-storage.md), [architecture/components.md](../architecture/components.md), [observation/event-model.md](../observation/event-model.md).
