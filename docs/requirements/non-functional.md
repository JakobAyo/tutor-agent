# Non-Functional Requirements

> **Responsibility:** Quality constraints: latency, cost, privacy, how often it may interrupt.

- **Non-blocking hook:** the hook returns within about 100 ms and starts detection in the background. The agent never waits for the tutor.
- **No self-observation:** `claude -p` calls started by the tutor must not trigger the tutor's hooks ([0003](../decisions/0003-claude-p-subscription-runtime.md)).
- **Usage budget:** at most one detection call per finished agent turn, never one per tool call. Very small turns (for example no code changes and no commands) are skipped without an LLM call.
- **Interruption limit:** at most one desktop notification per agent turn, and notifications can be muted.
- **Secrets:** the setup token lives only in `.env`, which is git-ignored. Hooks and logs never print it.
- **Privacy:** transcripts and the concept memory stay on my machine, except for what `claude -p` sends to Anthropic.
- **Robustness:** a crash in detection must never surface in the agent session. Errors go to a tutor log file.
- **Concurrency:** several agent sessions may detect at the same time, so writes to the concept memory must be safe (locking or atomic replace).
