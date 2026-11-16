# 0010: Project tooling is uv with Python 3.12+

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
[0004](0004-python.md) chose Python but left the version and the packaging tooling open. The tutor is installed as a single CLI that a global Claude Code hook calls.

## Decision
- **uv** manages dependencies, the lockfile, and the virtual environment.
- The minimum version is **Python 3.12**.
- The CLI is installed with `uv tool install`, so the hook can call it from any project.

## Alternatives considered
- pip + venv: works, but has no lockfile and is slower.
- Poetry: mature, but slower and heavier than uv, and has no advantage here.

## Consequences
- One tool handles installs, lockfile, and running scripts. Builds can be reproduced from the lockfile.
- Updated: [architecture/tech-stack.md](../architecture/tech-stack.md).
