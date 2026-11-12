# Tech Stack

> **Responsibility:** Languages, frameworks, models, and tools in use, with versions.

| Area | Choice | Decision |
|---|---|---|
| Language | Python 3.12+ | [0004](../decisions/0004-python.md), [0010](../decisions/0010-uv-and-python-312.md) |
| LLM access | `claude -p` (headless Claude Code CLI) on my subscription | [0003](../decisions/0003-claude-p-subscription-runtime.md) |
| Models | Cheap model (Haiku class) for detection, strong model (Sonnet/Opus class) for lessons and follow-ups, both set in settings | [0016](../decisions/0016-model-per-job.md) |
| Auth | Existing Claude Code login, or a token from `claude setup-token` in the data directory's `.env` | [0003](../decisions/0003-claude-p-subscription-runtime.md), [0019](../decisions/0019-token-in-data-directory.md) |
| Observation | Claude Code hooks + JSONL transcripts | [0002](../decisions/0002-observe-claude-code-only.md) |
| Notifications | `notify-send` (Linux) | [0007](../decisions/0007-interaction-model.md) |
| LLM sandboxing | `claude -p` with all tools disabled, run from the data directory | [0011](../decisions/0011-sandboxed-claude-calls.md) |
| Concept memory | One JSON file in `~/.local/share/tutor-agent/` | [0008](../decisions/0008-concept-memory-json.md) |
| TUI | Textual | [0009](../decisions/0009-textual-tui.md) |
| Packaging/tooling | uv, installed with `uv tool install` | [0010](../decisions/0010-uv-and-python-312.md) |
