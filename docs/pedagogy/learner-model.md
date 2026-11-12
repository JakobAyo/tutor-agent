# Learner Model

> **Responsibility:** How my knowledge, gaps, and progress are represented and updated.

Decided in [0005](../decisions/0005-global-concept-memory.md): one **global concept memory** with a status per concept.

## Statuses
| Status | Meaning | Set by |
|---|---|---|
| `new` | Detected, not opened yet | Detector |
| `seen` | Lesson opened at least once | Tutor pane, when I open it |
| `understood` | I can explain it | Me, by hand |
| `dismissed` | Not worth learning, never detect again | Me, by hand |

## Updates
- The detector only **adds** concepts. It never changes the status of an existing one.
- When a known concept shows up again, the detector adds the new source reference to it but sends no notification.
- Gaps = everything in `new` + `seen`. Progress = the number of concepts in `understood` over time.

Storage details: [data storage](../architecture/data-storage.md).
