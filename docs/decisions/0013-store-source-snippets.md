# 0013: Each source reference stores a short code snippet

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
Lessons start from the real code where a concept appeared ([0005](0005-global-concept-memory.md)). Until now a source reference was only a pointer into the session transcript. Claude Code deletes old transcripts (`cleanupPeriodDays`, 30 days by default), so lessons for older concepts would lose their code. Also, [0011](0011-sandboxed-claude-calls.md) means lessons only see what the tutor puts into the prompt.

## Decision
- When the detector stores a concept or adds a source to it, it saves a **short snippet**: the relevant code, diff, or command, plus one line about what the agent was doing. The snippet is capped in size (about 40 lines).
- The transcript pointer is kept too, but only as optional extra context. Lessons work from the snippet alone.
- A lesson uses the **most recent** source by default.

## Alternatives considered
- References only: the concept memory stays small, but sources vanish when transcripts are cleaned up.
- Raise `cleanupPeriodDays`: it changes a global Claude Code setting for the tutor's sake, and the code is still lost if transcripts are deleted by hand.

## Consequences
- Lessons stay tied to real code no matter how old the concept is.
- The concept memory grows with every source. If it gets too large, keep only the last few sources per concept.
- Snippets may contain code from any project, which is fine because the concept memory stays local ([non-functional requirements](../requirements/non-functional.md)).
- Updated: [architecture/data-storage.md](../architecture/data-storage.md), [architecture/components.md](../architecture/components.md), [pedagogy/teaching-strategy.md](../pedagogy/teaching-strategy.md), [glossary/terms.md](../glossary/terms.md).
