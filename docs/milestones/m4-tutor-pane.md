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
- [ ] Every status change from the [learner model](../pedagogy/learner-model.md) works and is saved.
- [ ] A lesson quotes the real snippet, then generalizes, covers trade-offs, and gives 2–3 links.
- [ ] Reopening a lesson makes no LLM call.
- [ ] The pane stays responsive while a lesson is generated and while the detector writes.
