<!-- PR title must be a Conventional Commit, e.g. "feat: add quiz mode" or "fix(reader): handle truncated lines".
     It becomes the squash-commit message that drives the version bump and the CHANGELOG. -->

## What and why

## How I tested it

## Checklist
- [ ] Targets `develop` (only `develop`, `release-please--*` and `hotfix/*` may target `main`)
- [ ] Tests added or updated; `uv run pytest --cov` passes
- [ ] New design decision? An ADR is added in `docs/decisions/`
- [ ] No hand edits to `CHANGELOG.md` or the version
