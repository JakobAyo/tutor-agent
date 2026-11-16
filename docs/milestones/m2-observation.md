# M2: Observation Pipeline

> **Responsibility:** Turn finished agent turns into event batches, without any LLM calls yet.

## Goal
Every finished agent or subagent turn in any session produces a correct batch of new events, and the agent session never notices.

## Scope
- **Hook entry:** light imports, reads the hook JSON, exits at once on the recursion guard, starts `tutor detect` detached, exits 0 ([0004](../decisions/0004-python.md)).
- **Transcript reader:** JSONL → events using the M0 mapping. Offsets per session and per subagent transcript, with a per-session lock so two close hooks don't read the same lines twice ([0015](../decisions/0015-include-subagent-activity.md)). Long outputs truncated.
- **Pre-filter:** skip turns with no edits, no commands, and no real reasoning ([triggers](../observation/triggers.md)).
- **Install:** `tutor install` adds the hook to the global Claude Code settings, after showing the change and making a backup. `tutor uninstall` removes it.
- **Debugging:** `tutor detect --dry-run` writes the batch to the log instead of calling the LLM.

## Out of scope
The detection prompt, concept storage, notifications.

## Done when
- [x] The hook returns in about 100 ms (measured).
- [x] In real sessions, including ones with subagents, each batch holds exactly the new events.
- [x] A crash in `tutor detect` shows up only in the tutor log, never in the agent session.
- [x] Reader and pre-filter are tested with the M0 fixture transcripts.

## Results (2026-11-12)
Decisions: [0025](../decisions/0025-byte-offsets-per-session.md) (offsets, lock, backlog cap), [0026](../decisions/0026-hook-handoff-and-install.md) (hook handoff, install).

| Item | Evidence |
|---|---|
| Hook time | Installed tool (`~/.local/bin/tutor hook`), 20 runs each: median 35 ms (max 44 ms) when it starts `tutor detect`, 19.5 ms when the recursion guard exits early |
| Crash isolation | `tests/test_hook.py`: a missing transcript and a bad payload give exit 0, empty stdout and stderr, and a traceback in `tutor.log` |
| Exactly the new events | `tests/test_reader.py`: incremental reads, partial last line, broken line, shrunk file, subagent offsets in the same session file. 4 processes reading while a writer appends 50 turns see every turn exactly once; with the lock removed the test fails (3 of 3 runs) |
| Reader and pre-filter | The M0 fixtures are event batches, not raw transcripts, so the reader is tested on synthetic transcripts with the M0 record shapes (`tests/transcripts.py`). The pre-filter passes all five M0 batches and skips short chat |
| Install | `tests/test_install.py`: keeps other hooks, idempotent, replaces an old path, uninstall restores the original, backup, file mode kept, refuses invalid JSON. Not yet run on the real `~/.claude/settings.json` |
| Offline tests | `uv run pytest`: 96 tests |

## Real-session check (2026-11-13)
`tutor install` ran on the real `~/.claude/settings.json`; `tutor.log` covers 6 sessions over a day of normal use.

| Item | Evidence |
|---|---|
| Exactly the new events | Per session, the batch line ranges are contiguous with no gaps or overlaps (e.g. `7eb1f325`: 1-50, 51-70, … 444-460, 461-468) |
| Background subagents | Session `64223d39` ran two background subagents. Main `Stop` (174-185), subagent batch (1-104), second `Stop` after it finished (186-190), second subagent (1-281). Each transcript keeps its own offset, nothing read twice |
| Ghost `SubagentStop` | About 1 s after most `Stop`s, a `SubagentStop` names an `agent-a<hex>.jsonl` that is never written (23 cases, also in sessions without any subagent): an internal Claude Code helper agent. It used to log a `FileNotFoundError` traceback; now `tutor detect` logs one `skip … no transcript (internal agent)` line. A missing main transcript is still an error |
