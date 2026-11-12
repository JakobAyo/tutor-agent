# 0014: All Claude Code sessions are observed

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
The hook is installed in the global Claude Code settings ([0002](0002-observe-claude-code-only.md)), so it fires in every project. The open question was whether to limit observation to some projects.

## Decision
The tutor observes **every** Claude Code session. There is no allowlist or denylist for now.

## Alternatives considered
- Allowlist: full control, but every new project has to be added by hand, and concepts get missed (goal 1 in [goals](../vision/goals.md)).
- Denylist: keeps sensitive repos out, but no such need exists yet.

## Consequences
- Nothing is missed, and there's nothing to configure.
- Snippets from every project end up in the local concept memory ([0013](0013-store-source-snippets.md)).
- A project filter can be added later through a new ADR. The hook entry is the natural place for it.
- Updated: [observation/sources.md](../observation/sources.md).
