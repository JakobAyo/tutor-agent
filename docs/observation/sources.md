# Observation Sources

> **Responsibility:** Which agents and signals are watched (transcripts, diffs, commands, hooks).

Decided in [0002](../decisions/0002-observe-claude-code-only.md): **Claude Code only**. **Every** session in every project is observed ([0014](../decisions/0014-observe-all-sessions.md)).

| Signal | Where it comes from | What it gives the tutor |
|---|---|---|
| Hook event | A Claude Code hook (for example `Stop` at the end of an agent turn, `SubagentStop` at the end of a subagent), installed in my global settings | The trigger, plus the session id, the working directory, and the transcript path |
| Session transcript | The JSONL file under `~/.claude/projects/...` | Assistant reasoning, tool calls (edits, writes, bash commands) and their results |
| Subagent transcripts | Sidechain JSONL files written by subagents (Task tool) | The subagent's own code, commands, and reasoning ([0015](../decisions/0015-include-subagent-activity.md)) |

- The tutor reads transcripts **incrementally**. It remembers the last processed position per session and per subagent transcript, and only reads newer lines.
- File diffs come from the Edit/Write tool calls in the transcript. Running git is not needed.

## Hook triggers
Both `Stop` and `SubagentStop` are used, each as its own trigger ([0021](../decisions/0021-subagentstop-trigger.md)). `PostToolUse` is not used: it would fire once per tool call. Payload fields (verified in M0 on Claude Code 2.1.322, sample in `spike/results/hook-payloads.json`):

| Field | `Stop` | `SubagentStop` | Use |
|---|---|---|---|
| `session_id`, `cwd`, `transcript_path` | yes | yes | Session identity and the main transcript |
| `hook_event_name` | yes | yes | Pick the handler |
| `agent_id`, `agent_type`, `agent_transcript_path` | no | yes | The subagent transcript to read |
| `last_assistant_message` | yes | yes | Not needed: the transcript has it |
| `background_tasks` | yes | yes | Shows subagents still running when `Stop` fires |

- Hooks also fire in `claude -p` sessions, so the tutor's own calls must turn them off ([0022](../decisions/0022-claude-p-flag-set.md)).
- When a subagent runs in the background, `Stop` fires twice for one prompt: once while the subagent runs, and again after its result comes back. Offsets make this harmless.

## Transcript layout
- Main transcript: `~/.claude/projects/<cwd with / replaced by ->/<session_id>.jsonl`.
- Subagent transcripts: `<session_id>/subagents/agent-<agent_id>.jsonl`, all records with `isSidechain: true`. A sibling `agent-<agent_id>.meta.json` holds `agentType`, `description`, and the parent's `toolUseId`.
- The main transcript only contains the subagent's prompt and final summary (the `Agent` tool call and its result).

## Format stability
- M0 parsed all 381 local transcripts (Claude Code 2.1.289 to 2.1.322) with no invalid line.
- There are about 27 record types. Only `user` and `assistant` matter. Many others (`api-request-blob`, `attachment`, `file-history-delta`, ...) hold copies or metadata. The reader must **ignore unknown types**, not fail on them.
- Most `thinking` blocks are empty (91% in M0), so the agent's reasoning comes mainly from `text` blocks.
