# 0024: Settings live in an optional `settings.toml` in the data directory

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
[0016](0016-model-per-job.md) makes the model names settings, and the [non-functional requirements](../requirements/non-functional.md) ask for a mute switch. The installed `tutor` runs from any directory ([0019](0019-token-in-data-directory.md)), so settings can't live in the repo. I edit them by hand, rarely.

## Decision
- Settings are read from `~/.local/share/tutor-agent/settings.toml`. The file and every key are optional, and missing keys use defaults.
- Keys: `detect_model` (`haiku`), `lesson_model` (`sonnet`), `muted` (`false`), `claude_bin` (`claude`), `claude_timeout_s` (`120`).
- Unknown keys or wrong types are an error, so a typo doesn't fail silently.
- The tutor reads the file but never writes it. It's parsed with the standard library's `tomllib`.
- `TUTOR_AGENT_DATA_DIR` overrides the data directory. It exists for tests.

## Alternatives considered
- JSON: the tutor could write it (for example a `tutor mute` command), but it's unpleasant to edit by hand and has no comments.
- Environment variables: the hook runs in the observed session's environment, so they would be hard to set in one place.

## Consequences
- No extra dependency, and the file can carry comments.
- Muting means editing a file. If that turns out to be too slow in daily use (M6), add a command that writes a separate flag file.
- Updated: [architecture/data-storage.md](../architecture/data-storage.md), [architecture/tech-stack.md](../architecture/tech-stack.md).
