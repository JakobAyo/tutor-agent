# 0005: One global concept memory with a simple status per concept

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
The tutor needs to know which concepts I've already met, so that it only notifies me about new ones. Concepts such as "dependency injection" repeat across projects.

## Decision
- One **global** concept memory file shared by all projects. It lives outside any repo, in my home directory.
- Each concept has a status: `new` → `seen` → `understood`.
  - `new`: detected, but I haven't opened it yet.
  - `seen`: I opened the lesson.
  - `understood`: I marked it myself. The tutor never sets this status.
- Each concept keeps a reference to where it was found (session, file), so a lesson can show the real code.

## Alternatives considered
- A 0–5 confidence score: more precise, but it needs assessment to update it, and quizzes are dropped for now ([0006](0006-drop-socratic-quizzes-for-now.md)).
- Per-project memory: concepts are mostly independent of the project, so separate files would cause repeated notifications.

## Consequences
- Simple to implement and easy to inspect or edit by hand.
- "Understood" is a self-assessment, so it can be over-optimistic.
- Open question: the file format (JSON or Markdown) and its exact path. See [data storage](../architecture/data-storage.md).
- Updated: [pedagogy/learner-model.md](../pedagogy/learner-model.md).
