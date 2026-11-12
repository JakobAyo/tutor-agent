# 0018: Add a `dismissed` status to the concept memory

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
[0005](0005-global-concept-memory.md) defined three statuses: `new` → `seen` → `understood`. F10 in the [functional requirements](../requirements/functional.md) and the [triggers](../observation/triggers.md) also need a way to say "not worth learning, never detect again". The [learner model](../pedagogy/learner-model.md) already listed `dismissed`, but no ADR covered it.

## Decision
- This extends 0005 with a fourth status: **`dismissed`**.
- I set it by hand in the tutor pane, from any other status. The tutor never sets it.
- A dismissed concept stays in the concept memory. Its name stays in the known-names list given to the detector, so the concept is never reported as new again.
- New sources for a dismissed concept are not recorded, and no notification is sent.
- I can undo a dismissal by setting the concept back to `new`.

## Alternatives considered
- Delete dismissed concepts: the file stays smaller, but the detector would find the concept again and notify me again.
- A separate ignore list: it would duplicate the concept memory with a second file to keep in sync.

## Consequences
- Dismissed concepts never come back as notifications.
- The pane hides dismissed concepts by default and can show them on request.
- Updated: [pedagogy/learner-model.md](../pedagogy/learner-model.md), root `CLAUDE.md`.
