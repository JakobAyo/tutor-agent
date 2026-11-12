# Data Storage

> **Responsibility:** What is persisted (learner model, lesson history), where, and in what format.

All of it is stored locally, outside any project repo, in the tutor data directory `~/.local/share/tutor-agent/`.

| Data | Content | Notes |
|---|---|---|
| **Concept memory** | Per concept: name, category, status, short summary, source references, timestamps. Each source reference holds a short snippet (code, diff, or command, about 40 lines max) plus the transcript pointer | One global JSON file ([0005](../decisions/0005-global-concept-memory.md), [0008](../decisions/0008-concept-memory-json.md)). Writes go to a temp file and replace the original atomically while a lock is held. Snippets keep lessons working after transcripts are cleaned up ([0013](../decisions/0013-store-source-snippets.md)). |
| **Transcript offsets** | Per session and per subagent transcript: byte position and line of the last processed line | `offsets/<session_id>.json`, one file per session, changed under `offsets/<session_id>.lock`. So that each batch only contains new events ([0015](../decisions/0015-include-subagent-activity.md), [0025](../decisions/0025-byte-offsets-per-session.md)) |
| **Lesson cache** | Generated lesson text per concept | Generated on first open, regenerated only on request. Also used as context for follow-ups ([0017](../decisions/0017-lesson-cache.md)) |
| **Settings** | Model per job, mute switch, `claude` path, call timeout | `settings.toml`, optional, read-only for the tutor ([0024](../decisions/0024-settings-toml.md)) |
| **Log** | Detector and runner errors | `tutor.log`, rotated at 1 MB. A filter masks the token in every record, including tracebacks |

Files: `concepts.json` (concept memory, format `{"version": 1, "concepts": [...]}`), `concepts.json.lock` (writer lock), `offsets/` (transcript offsets and their locks), `settings.toml`, `tutor.log`, `.env`.

Secrets: if a `claude setup-token` token is needed, it lives in `.env` in the data directory with permissions `600`. It is never kept in the tutor repo ([0019](../decisions/0019-token-in-data-directory.md)).
