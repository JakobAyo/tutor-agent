# 0030: Snippets point at code, and lessons teach from the best code source

- **Status:** Accepted
- **Date:** 2026-11-13

## Context
The first day of real use (M6 log) showed that most stored snippets were not code, even on code-heavy turns. Three concepts shared one `git commit` message, three shared the final summary of a turn, "Atomic file replacement" pointed at `cat` output, and "Lazy import" pointed at a test diff while the import was written in `cli.py`. The detection prompt only said "preferably code or a command", and a commit message *is* a command. Lessons then made it worse: they teach from the most recent source ([0013](0013-store-source-snippets.md)), and the most recent mention of a concept is usually a commit or a summary, so a good code source from an earlier turn was replaced by chat text.

## Decision
- **Detection prompt:** `event_index` is the event where the concept is implemented or used. Order of preference: an edit that writes the code, a command that uses it, output that shows the code, and the agent's reasoning only if none of these shows it. An edit to the main code beats an edit to its tests. A commit message or a summary of finished work is never picked when an earlier event shows the code. Each concept should point at its own event.
- **Sources store the event kind** (`Source.kind`: `edit`, `command`, `tool_result`, `reasoning`, `prompt`). Sources stored before this have no kind.
- **Lessons teach from the most recent source among the best-ranked ones:** an edit (or, for old sources, any source with a `file`) ranks above a command or its output, which ranks above prose. A newer edit still replaces an older one, so the "most recent" rule of [0013](0013-store-source-snippets.md) holds within a rank.
- **Regression fixture:** the real batch where this showed (`tests/fixtures/batches/tutor-store-and-pane.json`, home path anonymized) is in the `prompt` tests. It checks that every pick is code or code output, at least one is an edit, none is a doc, and a test file is picked only for a testing concept.

## Alternatives considered
- Code-only fix (rewrite the picked event to the nearest edit): the code can't tell which edit belongs to which concept; only the model can.
- Skip concepts whose only evidence is prose: loses real concepts the agent explained in reasoning, for example a trade-off with no code yet.
- Re-rank old sources by guessing the kind from the snippet text: brittle. `file` already marks old edits, which is the case that matters.

## Consequences
- On the regression batch, Haiku now picks the `tui.py` and `lessons.py` edits instead of the commit message (one run; the model is not deterministic, the M6 log keeps watching).
- A turn that only commits or summarizes still creates a prose source, but it no longer replaces an earlier code source in the lesson.
- Cached lessons are not regenerated automatically; `r` in the pane rebuilds one from the new choice.
- Updated: [pedagogy/teaching-strategy.md](../pedagogy/teaching-strategy.md), [architecture/components.md](../architecture/components.md), [architecture/data-storage.md](../architecture/data-storage.md), [milestones/m6-daily-use.md](../milestones/m6-daily-use.md).
