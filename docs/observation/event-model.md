# Event Model

> **Responsibility:** The normalized shape of an observed agent event, and how JSONL records map to it.

The transcript reader turns raw Claude Code JSONL lines into events of this shape. Everything after the reader only sees events.

| Field | Type | Meaning |
|---|---|---|
| `session_id` | string | Claude Code session |
| `agent_id` | string? | Subagent id, empty for the main agent |
| `project` | string | Working directory of the session |
| `timestamp` | ISO datetime | When the event happened |
| `kind` | `prompt` \| `reasoning` \| `edit` \| `command` \| `tool_result` | What happened |
| `file` | string? | File touched (for `edit`) |
| `content` | string | The text, diff, or command (truncated for long outputs) |
| `transcript_ref` | string | Absolute transcript path and 1-based line number (`path:line`), to find the source again |

## Mapping from JSONL
Drafted in M0 (`spike/extract_events.py`), implemented in `src/tutor_agent/events.py`.

| JSONL record | Event |
|---|---|
| `user` with text content, no `toolUseResult`, not `isMeta`, not a `<command-…>` / `<local-command-…>` / `<task-notification>` / `<system-reminder>` wrapper | `prompt`: the user's request, which tells the tutor *why* the agent acted |
| `assistant` content block `text` (non-empty) | `reasoning` |
| `assistant` content block `thinking` (only when non-empty) | `reasoning` |
| `assistant` `tool_use` named `Edit`, `MultiEdit`, `Write`, `NotebookEdit` | `edit`: `file` = `input.file_path`; content = old/new strings, or the written file |
| `assistant` `tool_use` named `Bash` | `command`: `input.command` |
| `user` `tool_result` whose `tool_use_id` belongs to a `Bash` call | `tool_result` (truncated harder: about 800 chars) |
| Everything else (Read/Grep results, `attachment`, `api-request-*`, …) | ignored |

## Notes
- A **batch** is all events since the last processed line of one transcript (main or subagent). A batch is the unit of detection.
- One batch can be large: M0 batches held 11 to 108 events, about 5k to 34k input tokens.
- A batch keeps at most the newest 150 events. More is a backlog, for example the tutor installed mid-session ([0025](../decisions/0025-byte-offsets-per-session.md)).
- Long contents are cut, to save usage. Limits: 2000 chars per event, 800 for `tool_result`.
  - Prompts, reasoning, commands, and command output keep whole lines from the start and the end, and cut the middle.
  - Edits keep whole hunks, because a middle cut lost half a function in an M0 lesson and stored snippets come from these events ([0013](../decisions/0013-store-source-snippets.md)). First the old sides go, then whole trailing hunks. Only a single oversized hunk is cut, keeping its first lines. `Write` keeps the top of the file.
- A line without a trailing newline is still being written: the reader stops before it and reads it next time. A complete line that isn't valid JSON is skipped and logged.
- A `tool_result` counts only if its `Bash` call is in the same batch. A turn holds both, so this loses nothing in practice.
