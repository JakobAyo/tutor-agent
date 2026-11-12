# M1: Foundation

> **Responsibility:** The project skeleton and the shared building blocks every later milestone uses.

## Goal
An installable `tutor` CLI with a concept store and a Claude runner that are safe to use, tested without spending subscription usage.

## Scope
- **Project:** uv project, Python 3.12+, one package, `tutor` CLI with subcommand stubs (`hook`, `detect`, `tui`) ([0004](../decisions/0004-python.md), [0010](../decisions/0010-uv-and-python-312.md)).
- **Paths and settings:** data directory `~/.local/share/tutor-agent/`, model names per job, mute switch.
- **Concept store:** schema for concepts, statuses (`new`, `seen`, `understood`, `dismissed`), and source references with snippets. File lock plus atomic replace ([0008](../decisions/0008-concept-memory-json.md), [0013](../decisions/0013-store-source-snippets.md), [0018](../decisions/0018-dismissed-status.md)).
- **Claude runner:** the flags found in M0, recursion guard, optional token from the data directory, timeout, model per call ([0011](../decisions/0011-sandboxed-claude-calls.md), [0016](../decisions/0016-model-per-job.md), [0019](../decisions/0019-token-in-data-directory.md)).
- **Logging:** a log file in the data directory that never contains the token.
- **Tests:** a fake `claude` binary for runner tests, and a test with several processes writing to the store at once.

## Out of scope
Hooks, transcripts, prompts, UI.

## Done when
- [ ] `uv tool install .` installs `tutor`, and the subcommands run from any directory.
- [ ] Parallel writes to the store never lose or corrupt data (tested).
- [ ] A real runner call returns JSON, runs with no tools from the data directory, and does not fire the hook.
- [ ] All tests pass without calling the real `claude`.
