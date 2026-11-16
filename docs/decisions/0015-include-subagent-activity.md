# 0015: Subagent activity is observed too

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
Claude Code agents hand work to subagents (Task tool). Subagents write to their own sidechain transcripts and fire `SubagentStop`, not `Stop`. If the tutor only reads the main transcript, it misses much of the code the agents actually write.

## Decision
- Detection includes subagent work.
- The exact way is confirmed in the spike. Either the tutor handles `SubagentStop` as its own trigger, or the `Stop` handler also reads the subagent transcripts of that turn.
- Each subagent transcript has its own read offset, just like a session.

## Alternatives considered
- Main transcript only: simpler, but it only sees the subagent's final summary, not its code, commands, or reasoning.

## Consequences
- Better coverage of what agents really do.
- More detection triggers per turn. The usage budget still applies: at most one detection call per finished agent or subagent turn ([non-functional requirements](../requirements/non-functional.md)).
- The transcript reader has to find and read sidechain transcripts.
- Updated: [observation/sources.md](../observation/sources.md), [requirements/non-functional.md](../requirements/non-functional.md).
