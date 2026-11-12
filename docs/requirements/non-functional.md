# Non-Functional Requirements

> **Responsibility:** Quality constraints: latency, cost, privacy, how often it may interrupt.

- **Non-blocking hook:** the hook returns within about 100 ms and starts detection in the background. The agent never waits for the tutor. (M0: a minimal Python hook takes about 25 ms, almost all of it interpreter start-up.)
- **No self-observation:** `claude -p` calls started by the tutor must not trigger the tutor's hooks, and must not leave transcripts behind ([0003](../decisions/0003-claude-p-subscription-runtime.md), [0022](../decisions/0022-claude-p-flag-set.md)).
- **No side effects:** the tutor's `claude -p` calls have no tools and never run inside an observed project, so they can't change any code ([0011](../decisions/0011-sandboxed-claude-calls.md)).
- **Usage budget:** at most one detection call per `Stop` or `SubagentStop` trigger ([0015](../decisions/0015-include-subagent-activity.md), [0021](../decisions/0021-subagentstop-trigger.md)), never one per tool call. Very small turns (for example no code changes and no commands) are skipped without an LLM call. Detection uses a cheaper model than lessons ([0016](../decisions/0016-model-per-job.md)).
- **Interruption limit:** at most one desktop notification per agent turn, and notifications can be muted.
- **Secrets:** the setup token, if used, lives only in the data directory's `.env` (permissions `600`), never in a repo ([0019](../decisions/0019-token-in-data-directory.md)). Hooks and logs never print it.
- **Privacy:** transcripts and the concept memory stay on my machine, except for what `claude -p` sends to Anthropic.
- **Robustness:** a crash in detection must never surface in the agent session. Errors go to a tutor log file.
- **Concurrency:** several agent sessions may detect at the same time, so writes to the concept memory must be safe (locking or atomic replace).
