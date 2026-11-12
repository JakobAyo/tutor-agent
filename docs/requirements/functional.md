# Functional Requirements

> **Responsibility:** The capabilities the tutor must provide.

## Detect
- **F1:** When a Claude Code agent finishes a turn, the tutor checks the new activity (code, commands, reasoning) for concepts.
- **F2:** A candidate concept is kept only if it is (a) not already in the concept memory and (b) worth knowing by the [filter rules](../observation/triggers.md).
- **F3:** Each kept concept is stored as `new`, with a reference to where it appeared (project, session, file or command).

## Notify
- **F4:** A desktop notification names the new concept(s). One notification per detection batch, not one per concept.

## Learn (tutor pane)
- **F5:** The TUI lists concepts by status, with `new` first.
- **F6:** Opening a concept shows a lesson: what the agent did, why, the general concept, and when *not* to use it, plus reading links. Opening it sets the status to `seen`.
- **F7:** I can mark a concept `understood`, or reset it to `seen`.
- **F8:** I can ask "explain what just happened" about the latest activity in a chosen session.
- **F9:** I can ask follow-up questions about an open lesson.
- **F10:** I can dismiss a concept as not worth learning, so it is never detected again.
