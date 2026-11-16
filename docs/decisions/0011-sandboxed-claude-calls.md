# 0011: The tutor's `claude -p` calls run with no tools from a neutral directory

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
Every LLM call is a `claude -p` subprocess ([0003](0003-claude-p-subscription-runtime.md)). By default, such a call loads the `CLAUDE.md` of its working directory and can use tools, including editing files and running commands. If a call were started in the observed project, it could change that project. That breaks the "no code writing" and "no interrupting the agent" non-goals. The project's instructions would also leak into the tutor's prompts.

## Decision
- Every `claude -p` call made by the tutor runs with **all tools disabled**. It only reads its prompt and returns text or JSON.
- The working directory is a **neutral directory** (the tutor data directory), never the observed project.
- All context the call needs (events, code snippets, the concept list) is put into the prompt by the tutor itself.
- The Claude runner is the only component that enforces this ([components](../architecture/components.md)).

## Alternatives considered
- Read-only tools (Read, Grep) inside the project: lessons could look up more code on their own, but the agent could wander off, and it would cost more usage and be harder to predict.
- Trust the prompt to say "don't edit": not a real safeguard.

## Consequences
- The tutor can't change any project, even through a bad prompt or prompt injection from a transcript.
- Lessons only see what the tutor gives them, so the transcript reader must collect enough source context.
- The exact CLI flags for disabling tools are confirmed in the spike.
- Updated: [architecture/components.md](../architecture/components.md), [requirements/non-functional.md](../requirements/non-functional.md).
