# 0001: Docs structure follows the Single Responsibility Principle

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
Project decisions and design notes need a home that stays easy to navigate as the project grows, both for me and for agents that load the docs as context.

## Decision
- `docs/` is split into folders that each answer one question: vision, requirements, pedagogy, observation, architecture, decisions, glossary.
- Each file covers one topic.
- `docs/CLAUDE.md` is only an index of the folders.
- Decisions are recorded as ADRs in `decisions/`. Topic folders describe the current state.

## Alternatives considered
- A single large design doc: easy to start, but it turns hard to navigate and expensive to load as context.
- Decisions only, with no topic folders: history is kept, but finding the current state means replaying every ADR.

## Consequences
- More files, but each one is small and focused, so an agent can load only what it needs.
- Every new decision means writing an ADR and updating the affected topic file.
