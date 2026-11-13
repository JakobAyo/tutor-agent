# M4: Tutor Pane, Browse and Lessons

> **Responsibility:** The TUI for browsing concepts, reading lessons, and changing statuses.

## Goal
In a separate terminal pane I can see my concept queue, open a lesson tied to real code, and track my progress (F5, F6, F7, F10).

## Scope
- **Concept list:** grouped by status with `new` first, showing category and source project. Dismissed concepts hidden by default. Refreshes when the concept memory changes ([0009](../decisions/0009-textual-tui.md)).
- **Lesson view:** generated with the strong model in the [lesson structure](../pedagogy/teaching-strategy.md), from the most recent snippet, rendered as Markdown. Generated in the background with a loading state, so the UI never freezes.
- **Lesson cache:** used on reopen, plus a "regenerate" key ([0017](../decisions/0017-lesson-cache.md)).
- **Status actions:** opening a lesson sets `seen`. Keys to mark `understood`, reset to `seen`, dismiss, and undo a dismissal ([0018](../decisions/0018-dismissed-status.md)).

## Out of scope
Follow-up questions, "explain what just happened".

## Done when
- [x] Every status change from the [learner model](../pedagogy/learner-model.md) works and is saved.
- [x] A lesson quotes the real snippet, then generalizes, covers trade-offs, and gives 2–3 links.
- [x] Reopening a lesson makes no LLM call.
- [x] The pane stays responsive while a lesson is generated and while the detector writes.

## Results (2026-11-13)
Decision: [0028](../decisions/0028-lessons-and-tutor-pane.md) (lesson call, cache files, when the pane calls the model, polling, status keys).

| Item | Evidence |
|---|---|
| Status changes | `tests/test_tui.py`: `u`, `s`, `d`, `n` change and save the status, invalid moves change nothing, dismissed is hidden until `h`, Enter moves `new` to `seen` |
| Lesson quality | `uv run pytest -m prompt tests/test_lesson_prompt.py` (one Sonnet call, ~12 s): five sections in order, a line of the real snippet quoted, 2–3 links, under 700 words. A lesson on a real concept read well, but quoted chat text because that concept's snippet was chat text (M6 log) |
| No call on reopen | `tests/test_tui.py`: open, move away, reopen gives one call in total; `r` makes a second |
| Responsive | `tests/test_tui.py`: during a hanging call the loading state shows and keys still change statuses; a concept written by another store instance appears without a restart |
| Offline tests | `uv run pytest`: 151 tests |

Not checked: the links in real lessons can be made up (no tools). Checked in M6.
