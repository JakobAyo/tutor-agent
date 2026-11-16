# 0002: Observe Claude Code only, through hooks and transcripts

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
The tutor needs a way to see what coding agents do. Agents differ a lot in how observable they are. Supporting several of them at the start would spread the effort thin before the core teaching loop works.

## Decision
- The only observed agent is **Claude Code**.
- Observation uses Claude Code **hooks**, which fire at points in a session, together with the session **JSONL transcript** that the hook input points to.

## Alternatives considered
- IDE agents such as Cursor: an extension or file watching would be needed, which is much more work.
- Other CLIs (Codex, Aider, Gemini CLI): each has its own log format, and none are in use now.
- Agent-agnostic git diffs: works with any agent, but loses the reasoning, the commands, and *why* a change was made, and that is the core of what the tutor teaches.

## Consequences
- The design can rely on the Claude Code transcript format and hook payloads.
- Supporting another agent later means adding a new source behind the [event model](../observation/event-model.md), and that needs a new ADR.
- Updated: [observation/sources.md](../observation/sources.md).
