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
- [x] Each question has an answer backed by a run, a log, or a sample file.
- [x] Findings are written into the topic files (`observation/`, `architecture/`), and the "to verify" notes there are removed.
- [x] Every finding that changes a decision has a new ADR.
- [x] Anonymized fixture batches are saved for the M3 tests.

## Results (2026-11-12, Claude Code 2.1.322)
Scripts and evidence are in `spike/` (see its README). Details are in the linked topic files.

| # | Answer | Evidence |
|---|---|---|
| 1 | `SubagentStop` sends `agent_transcript_path`. `Stop` can fire while background subagents still run, so subagents get their own trigger ([0021](../decisions/0021-subagentstop-trigger.md), [sources](../observation/sources.md)) | `spike/results/hook-payloads.json` |
| 2 | Subagents write to `<session>/subagents/agent-<id>.jsonl`. Only `user`/`assistant` records matter, and most `thinking` blocks are empty. The mapping is in [event model](../observation/event-model.md) | `spike/survey_transcripts.py`, `spike/extract_events.py` |
| 3 | `--tools ""` alone is not enough (MCP connectors stay). The working set is `--tools "" --setting-sources "" --strict-mcp-config --no-session-persistence --system-prompt` ([0022](../decisions/0022-claude-p-flag-set.md)). `--bare` can't use OAuth | `spike/sandbox_test.sh` |
| 4 | `--setting-sources ""` stops hooks. `TUTOR_AGENT_INTERNAL=1` reaches the hook, and the guard skipped as expected. Both layers are kept | `spike/detach_hook.py` |
| 5 | A detached `claude -p` works with the existing login after the parent session has exited. No token is needed | `spike/detached_worker.py` |
| 6 | About 25 ms in total for a minimal hook, almost all Python start-up. 100 ms is realistic. Re-measure with the `uv tool` install in M2 | `spike/detach_hook.py` |
| 7 | Haiku is good enough. On 5 batches it found concepts of similar value to Sonnet's, honoured the known list, and returned valid structured output ([0023](../decisions/0023-structured-detection-output.md)). It is a little more likely to pick a narrow, project-specific concept | `spike/detect.py`, `spike/results/detection-runs.json`, `tests/fixtures/batches/` |
| 8 | Detection: Haiku 8–14 s, list-price cost about $0.001–0.008 per batch. Sonnet 7–8 s, about 17x the cost. Lesson: Sonnet ~14 s, Opus ~15 s, 4–5 s to the first token | `spike/detect.py`, `spike/lesson.py` |

Follow-ups for later milestones:
- **M2:** stored snippets need a cut that keeps whole hunks. A middle cut lost half a function in a lesson.
- **M2:** re-measure hook time with the installed package.
- **M4:** lessons take about 15 s, so the pane should stream them or show progress.
