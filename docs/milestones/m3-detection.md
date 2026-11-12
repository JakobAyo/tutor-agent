# M3: Detection and Notifications

> **Responsibility:** Find worth-knowing concepts in a batch, store them, and notify me.

## Goal
After a real agent turn, new worth-knowing concepts appear in the concept memory with a snippet, and one desktop notification names them (F1–F4).

## Scope
- **Detection prompt:** the [worth-knowing rules](../observation/triggers.md), categories from the [curriculum](../pedagogy/curriculum.md), and the known concept names, including dismissed ones ([0018](../decisions/0018-dismissed-status.md)). Runs on the cheap model ([0016](../decisions/0016-model-per-job.md)).
- **Output:** JSON, validated before use. Invalid output is logged and dropped, never half-stored.
- **Storing:** new concepts as `new` with a snippet. Known concepts get a new source and no notification. Dismissed concepts are skipped ([0013](../decisions/0013-store-source-snippets.md)).
- **Notifier:** one `notify-send` per batch, respecting the mute setting.

## Out of scope
Lessons and the TUI.

## Done when
- [ ] Prompt tests on the M0 fixtures: the expected concepts are found and basics are not.
- [ ] After a day of real use, the new concepts look sensible and near-duplicates are rare. Note both in the M6 log.
- [ ] Never more than one detection call and one notification per finished turn.
- [ ] Mute works.
