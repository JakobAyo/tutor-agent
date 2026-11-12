# Event Model

> **Responsibility:** The normalized shape of an observed agent event.

The transcript reader turns raw Claude Code JSONL lines into events of this shape. Everything after the reader only sees events.

| Field | Type | Meaning |
|---|---|---|
| `session_id` | string | Claude Code session |
| `project` | string | Working directory of the session |
| `timestamp` | ISO datetime | When the event happened |
| `kind` | `reasoning` \| `edit` \| `command` \| `tool_result` | What the agent did |
| `file` | string? | File touched (for `edit`) |
| `content` | string | The text, diff, or command (truncated for long outputs) |
| `transcript_ref` | string | Transcript path and line number, to find the source again |

## Notes
- A **batch** is all events since the last processed position in one session. A batch is the unit of detection.
- Long tool outputs are truncated before they are sent to the detector, to save usage.
- The exact mapping from JSONL to events is defined in the spike (see [sources](sources.md)).
