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
- [x] Prompt tests on the M0 fixtures: the expected concepts are found and basics are not.
- [ ] After a day of real use, the new concepts look sensible and near-duplicates are rare. Note both in the M6 log.
- [x] Never more than one detection call and one notification per finished turn.
- [x] Mute works.

## Results (2026-11-13)
Decision: [0027](../decisions/0027-detection-rules.md) (categories, known-name resolution, validation, snippet, notification).

| Item | Evidence |
|---|---|
| Prompt quality | `uv run pytest -m prompt` (6 Haiku calls, ~10 s and ~$0.007 each): all five fixtures give 3 concepts that match the M0 spike's ideas, no basics. E.g. supervisor-loop: "Supervisor with last-known-good rollback", "Least-privilege tool permissions for unattended agents", "Exit-code contract between supervisor and child process". With a known name in the list, the model did not report a near-duplicate of it. Haiku sometimes picks a narrow, technology-specific concept ("QML required properties and ComponentBehavior Bound"), as M0 noted |
| One call, one notification | `tests/test_pipeline.py`: two turns and a no-op run give 2 calls and 1 notification (the second turn found only known concepts). The offline suite puts a fake `claude` and `notify-send` first on `PATH` for every test, detached subprocesses included |
| Mute | `tests/test_pipeline.py`, `tests/test_notifier.py`: with `muted = true` concepts are stored, nothing is sent |
| Storing | Known → source attached, dismissed → nothing, renamed known → dropped, duplicate in a batch → once, invalid item → dropped, failed call → nothing stored and logged |
| Offline tests | `uv run pytest`: 135 tests |

Open: the day of real use (second item) needs the refreshed tool (`uv tool install --force --reinstall .`).
