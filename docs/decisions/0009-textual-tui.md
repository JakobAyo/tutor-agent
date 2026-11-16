# 0009: The tutor pane is built with Textual

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
The tutor pane ([0007](0007-interaction-model.md)) is an interactive TUI. It lists concepts by status, shows lessons as rendered text, and takes follow-up questions. It is written in Python ([0004](0004-python.md)).

## Decision
The tutor pane uses **Textual**.

## Alternatives considered
- A plain CLI with subcommands (`tutor list`, `tutor explain`): less work, but browsing a queue and asking follow-ups in a loop is awkward.
- prompt_toolkit or curses: lower-level, so lists, scrolling, and layout would have to be built by hand.

## Consequences
- Widgets for lists, Markdown rendering, and input are available out of the box, and async support keeps the UI responsive while `claude -p` runs.
- Textual is a heavy import, so it must only be imported by the TUI subcommand and never by the hook entry ([0004](0004-python.md)).
- Updated: [architecture/tech-stack.md](../architecture/tech-stack.md).
