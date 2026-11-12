# Observation Sources

> **Responsibility:** Which agents and signals are watched (transcripts, diffs, commands, hooks).

Decided in [0002](../decisions/0002-observe-claude-code-only.md): **Claude Code only**.

| Signal | Where it comes from | What it gives the tutor |
|---|---|---|
| Hook event | A Claude Code hook (for example `Stop` at the end of an agent turn), installed in my global settings | The trigger, plus the session id, the working directory, and the transcript path |
| Session transcript | The JSONL file under `~/.claude/projects/...` | Assistant reasoning, tool calls (edits, writes, bash commands) and their results |

- The tutor reads the transcript **incrementally**. It remembers the last processed position per session and only reads newer lines.
- File diffs come from the Edit/Write tool calls in the transcript. Running git is not needed.

## To verify in a spike
- Which hook event fits best (`Stop` vs `PostToolUse` batching) and the exact payload fields.
- How stable the transcript JSONL format is across Claude Code versions.
