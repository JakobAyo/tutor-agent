# Learner Model

> **Responsibility:** How my knowledge, gaps, and progress are represented and updated.

Decided in [0005](../decisions/0005-global-concept-memory.md): one **global concept memory** with a status per concept. `dismissed` was added in [0018](../decisions/0018-dismissed-status.md).

## Statuses
| Status | Meaning | Set by |
|---|---|---|
| `new` | Detected, not opened yet | Detector |
| `seen` | Lesson opened at least once | Tutor pane, when I open it |
| `understood` | I can explain it | Me, by hand |
| `dismissed` | Not worth learning, never detect again. Can be undone by setting it back to `new` | Me, by hand |

## Updates
- The detector only **adds** concepts. It never changes the status of an existing one.
- When a known concept shows up again, the detector adds the new source reference to it but sends no notification. Dismissed concepts get no new sources.
- The tutor pane hides dismissed concepts by default.
- Gaps = everything in `new` + `seen`. Progress = the number of concepts in `understood` over time.

Storage details: [data storage](../architecture/data-storage.md).
