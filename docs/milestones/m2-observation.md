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
- [ ] The hook returns in about 100 ms (measured).
- [ ] In real sessions, including ones with subagents, each batch holds exactly the new events.
- [ ] A crash in `tutor detect` shows up only in the tutor log, never in the agent session.
- [ ] Reader and pre-filter are tested with the M0 fixture transcripts.
