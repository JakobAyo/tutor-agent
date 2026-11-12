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

## To verify in a spike
- Which hook event fits best (`Stop` vs `PostToolUse` batching) and the exact payload fields.
- How subagent work is picked up: a `SubagentStop` trigger, or reading the subagent transcripts from the `Stop` handler. Also where sidechain transcripts are stored.
- How stable the transcript JSONL format is across Claude Code versions.
