# 0008: The concept memory is a single JSON file

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
[0005](0005-global-concept-memory.md) left the format of the global concept memory open (JSON or Markdown). Several detector processes may write to it at the same time, so writes must be safe ([non-functional requirements](../requirements/non-functional.md)). The detector, the store, and the tutor pane all read it.

## Decision
- The concept memory is **one JSON file** in the tutor data directory, `~/.local/share/tutor-agent/`.
- Writes go to a temporary file in the same directory and then replace the original atomically (`os.replace`), while a file lock is held.

## Alternatives considered
- One Markdown file per concept: easy to read and edit by hand, for example in Obsidian. But it needs parsing, and safe concurrent writes across many files are harder.
- SQLite: safe concurrency out of the box, but it's more machinery than a few hundred records need, and it's harder to inspect by hand.

## Consequences
- Simple to load and save from Python, and easy to validate.
- Reading it by hand is possible but less pleasant than Markdown. A Markdown export can be added later if needed.
- The whole file is rewritten on every change. That's fine at this size.
- Updated: [architecture/data-storage.md](../architecture/data-storage.md).
