# Tech Stack

> **Responsibility:** Languages, frameworks, models, and tools in use, with versions.

| Area | Choice | Decision |
|---|---|---|
| Language | Python (version to be pinned) | [0004](../decisions/0004-python.md) |
| LLM access | `claude -p` (headless Claude Code CLI) on my subscription | [0003](../decisions/0003-claude-p-subscription-runtime.md) |
| Auth | Token from `claude setup-token`, stored in `.env` | [0003](../decisions/0003-claude-p-subscription-runtime.md) |
| Observation | Claude Code hooks + JSONL transcripts | [0002](../decisions/0002-observe-claude-code-only.md) |
| Notifications | `notify-send` (Linux) | [0007](../decisions/0007-interaction-model.md) |
| TUI | Not chosen (candidate: Textual) | — |
| Packaging/tooling | Not chosen (candidate: uv) | — |
