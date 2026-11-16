# 0012: Follow-up questions are stateless and rebuild their context each time

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
F9 asks for follow-up questions about an open lesson. Each `claude -p` call is stateless. Continuing a call with `--resume` would create real Claude Code sessions under `~/.claude/projects/`, and the tutor would then have to keep them out of its own observation.

## Decision
Every follow-up is a fresh `claude -p` call. Its prompt is built from:
1. the **lesson context**: the source events, plus the lesson text (from the cache, or as generated),
2. the **conversation so far** in the tutor pane for this lesson,
3. **what I already know**, taken from the concept memory: related concepts that are `seen` or `understood`, so the answer can build on them and skip what I already know,
4. the new question.

## Alternatives considered
- `claude -p --resume <session-id>`: no context has to be rebuilt, but it creates hidden sessions that the recursion guard would also have to cover, and session state would live outside the tutor's own data.

## Consequences
- The tutor owns all state, and no extra Claude Code sessions are created.
- Prompts grow with long follow-up threads. If that becomes a problem, older turns can be trimmed.
- Answers can refer to what I already know, which fits the "skip basics" principle.
- Updated: [pedagogy/teaching-strategy.md](../pedagogy/teaching-strategy.md), [architecture/components.md](../architecture/components.md).
