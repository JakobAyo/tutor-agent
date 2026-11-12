# 0004: The tutor is written in Python

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
The tutor consists of a hook script, a background detector, a small data store, and a terminal UI. All of these are I/O and glue code. Nothing here is performance-critical.

## Decision
The tutor is a Python project. It is packaged as a single CLI that provides subcommands for the hook, the detector, and the TUI.

## Alternatives considered
- TypeScript/Node with Ink for the TUI: a good TUI story, but no real advantage for this project.

## Consequences
- Good libraries are available for the TUI (for example Textual), JSON handling, and subprocesses.
- Hook start-up time matters (see [non-functional requirements](../requirements/non-functional.md)), so the hook entry point must stay light on imports.
- Updated: [architecture/tech-stack.md](../architecture/tech-stack.md).
