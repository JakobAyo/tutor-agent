# Data Storage

> **Responsibility:** What is persisted (learner model, lesson history), where, and in what format.

All of it is stored locally, outside any project repo, in the tutor data directory `~/.local/share/tutor-agent/`.

| Data | Content | Notes |
|---|---|---|
| **Concept memory** | Per concept: name, category, status, short summary, source references, timestamps | One global JSON file ([0005](../decisions/0005-global-concept-memory.md), [0008](../decisions/0008-concept-memory-json.md)). Writes go to a temp file and replace the original atomically while a lock is held. |
| **Transcript offsets** | Per session: last processed line | So that each batch only contains new events |
| **Lesson cache** (optional) | Generated lesson text per concept | Avoids spending usage on the same lesson twice |
| **Log** | Detector and runner errors | Never contains the token |

Secrets: the `claude setup-token` token lives in `.env` in the tutor repo, which is git-ignored ([0003](../decisions/0003-claude-p-subscription-runtime.md)).
