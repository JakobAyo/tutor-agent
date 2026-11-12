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
| `transcript_ref` | string | Transcript path and line number, to find the source again |

## Mapping from JSONL
Drafted and tested in M0 (`spike/extract_events.py`).

| JSONL record | Event |
|---|---|
| `user` with text content, no `toolUseResult`, not `isMeta`, not a `<command-…>` / `<task-notification>` wrapper | `prompt`: the user's request, which tells the tutor *why* the agent acted |
| `assistant` content block `text` (non-empty) | `reasoning` |
| `assistant` content block `thinking` (only when non-empty) | `reasoning` |
| `assistant` `tool_use` named `Edit`, `MultiEdit`, `Write`, `NotebookEdit` | `edit`: `file` = `input.file_path`; content = old/new strings, or the written file |
| `assistant` `tool_use` named `Bash` | `command`: `input.command` |
| `user` `tool_result` whose `tool_use_id` belongs to a `Bash` call | `tool_result` (truncated harder: about 800 chars) |
| Everything else (Read/Grep results, `attachment`, `api-request-*`, …) | ignored |

## Notes
- A **batch** is all events since the last processed line of one transcript (main or subagent). A batch is the unit of detection.
- One batch can be large: M0 batches held 11 to 108 events, about 5k to 34k input tokens.
- Long contents are cut before they are sent to the detector, to save usage. A middle cut is fine for detection, but it lost half a function in an M0 lesson. Stored source snippets ([0013](../decisions/0013-store-source-snippets.md)) need a cut that keeps whole hunks.
- A partly written last line may fail to parse. The reader stops there and re-reads it next time.
