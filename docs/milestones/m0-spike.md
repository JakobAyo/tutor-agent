# M0: Spike

> **Responsibility:** Answer the open technical questions before any production code is written.

## Goal
Replace every "to verify in the spike" note in the docs with a tested answer. The spike code is throwaway: small scripts in `spike/`, which is not part of the package.

## Questions
1. **Hook payloads:** what do `Stop` and `SubagentStop` send on stdin (session id, transcript path, cwd, subagent transcript path)? Which trigger picks up subagent work best ([0015](../decisions/0015-include-subagent-activity.md))?
2. **Transcript format:** which record types exist, and how do reasoning, tool calls (Edit, Write, Bash), tool results, and sidechains appear? Where are subagent transcripts stored? Draft the JSONL → [event](../observation/event-model.md) mapping.
3. **Sandboxed calls:** which `claude -p` flags turn off all tools, set the model, and return JSON? Does a call from the data directory avoid loading any project `CLAUDE.md` ([0011](../decisions/0011-sandboxed-claude-calls.md))?
4. **Recursion guard:** does an environment variable, or turning hooks off through settings, reliably stop a tutor call from firing the tutor's hook ([components](../architecture/components.md))?
5. **Auth:** does `claude -p`, started detached from a hook, work with the existing login, or is a token needed ([0019](../decisions/0019-token-in-data-directory.md))?
6. **Non-blocking hook:** how long does a minimal Python hook take to start a detached process and exit? Is 100 ms realistic?
7. **Detection quality:** run a draft detection prompt on 3–5 real transcripts with the cheap and the strong model. Is the cheap model good enough ([0016](../decisions/0016-model-per-job.md))? Save these batches as test fixtures.
8. **Cost and latency:** how long does one detection call and one lesson call take?

## Out of scope
Packaging, the concept store, the TUI, error handling.

## Done when
- [ ] Each question has an answer backed by a run, a log, or a sample file.
- [ ] Findings are written into the topic files (`observation/`, `architecture/`), and the "to verify" notes there are removed.
- [ ] Every finding that changes a decision has a new ADR.
- [ ] Anonymized fixture batches are saved for the M3 tests.
