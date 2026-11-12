# Glossary

> **Responsibility:** Definitions of project-specific terms (e.g. teaching moment, learner model, observed agent).

| Term | Meaning |
|---|---|
| **Observed agent** | A Claude Code session that the tutor watches. |
| **Event** | One normalized agent action (reasoning, edit, command, tool result). See [event model](../observation/event-model.md). |
| **Batch** | All new events of one session since the last detection run. |
| **Concept** | A reusable piece of understanding (pattern, mechanism, trade-off), named at a general level. |
| **Worth knowing** | New to me *and* reusable beyond the current line of code. See [triggers](../observation/triggers.md). |
| **Concept memory** | The global file that stores every concept with its status and sources. |
| **Source reference** | Where a concept appeared (project, session, transcript line, file), plus a short stored snippet of the code, diff, or command. |
| **Lesson** | The explanation the tutor gives for one concept, starting from its source reference. |
| **Tutor pane** | The TUI running in a separate terminal pane. |
| **Detector** | The background process that finds concepts in a batch using `claude -p`. |
