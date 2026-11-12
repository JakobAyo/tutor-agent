# Data Storage

> **Responsibility:** What is persisted (learner model, lesson history), where, and in what format.

All of it is stored locally, outside any project repo, in a tutor data directory in my home (path to be decided, for example `~/.local/share/tutor-agent/`).

| Data | Content | Notes |
|---|---|---|
| **Concept memory** | Per concept: name, category, status, short summary, source references, timestamps | Global ([0005](../decisions/0005-global-concept-memory.md)). Writes use atomic replace and a lock. |
| **Transcript offsets** | Per session: last processed line | So that each batch only contains new events |
| **Lesson cache** (optional) | Generated lesson text per concept | Avoids spending usage on the same lesson twice |
| **Log** | Detector and runner errors | Never contains the token |

Secrets: the `claude setup-token` token lives in `.env` in the tutor repo, which is git-ignored ([0003](../decisions/0003-claude-p-subscription-runtime.md)).

## Open questions
- Format of the concept memory: JSON (easy to work with in code) or Markdown (easy to read and edit by hand, for example in Obsidian).
- Exact data directory path.
