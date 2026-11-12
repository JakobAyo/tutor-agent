# 0021: Subagent work is picked up through its own `SubagentStop` trigger

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
[0015](0015-include-subagent-activity.md) left open how subagent work reaches the detector: a separate `SubagentStop` trigger, or the `Stop` handler reading the subagent transcripts of that turn. The M0 spike captured real hook payloads (`spike/results/hook-payloads.json`):
- `SubagentStop` sends `agent_id`, `agent_type`, and `agent_transcript_path`, the path of the subagent's own JSONL file.
- Subagents often run in the **background**. The main agent's `Stop` then fires while the subagent is still running (`background_tasks[].status == "running"`), and a second `Stop` fires after the subagent's result comes back.

A `Stop` handler that reads subagent transcripts would see half-written transcripts and would have to guess when each one is finished.

## Decision
- The hook entry handles both `Stop` and `SubagentStop`.
- `Stop` reads the main transcript (`transcript_path`) from its offset.
- `SubagentStop` reads the subagent transcript (`agent_transcript_path`) from its offset.
- Each trigger produces at most one batch, and so at most one detection call.

## Alternatives considered
- `Stop` reads all `subagents/*.jsonl` of the session: no second hook, but it races with background subagents and needs extra logic to detect a finished transcript.

## Consequences
- Every subagent's work is seen exactly once, when it is complete.
- More triggers per user prompt. The pre-filter and the per-trigger budget keep usage in check.
- The main transcript only holds the subagent's final summary (the `Agent` tool result), so nothing is detected twice.
- Updated: [observation/sources.md](../observation/sources.md), [requirements/non-functional.md](../requirements/non-functional.md).
