# 0033: CI/CD, quality gates and automated releases

- **Status:** Accepted
- **Date:** 2026-11-16

## Context
The repo is public and meant for others to use and contribute to. Until now quality depended on me
running pytest by hand, versions were never bumped, and there was no changelog. Commits already
follow Conventional Commits.

## Decision
- **License:** MIT.
- **Quality gates** (`.github/workflows/ci.yml`, required on every PR): `uv lock --check`, ruff lint
  and format, mypy `--strict` on `src/` (tests in a relaxed pass), pytest on Python 3.12–3.14 with
  a 90% branch-coverage floor, `uv build` + `twine check` + a CLI smoke test from the wheel, and
  dependency review. One aggregate check, "CI passed", is the one marked required. CodeQL runs on
  PRs, pushes and weekly. The same tools run locally through pre-commit, from versions pinned in `uv.lock`.
- **Branch flow:** feature branches squash-merge into `develop`, and `develop` merge-commits into
  `main`. A PR-policy workflow enforces Conventional Commit PR titles and allows only `develop`,
  `release-please--*` and `hotfix/*` to target `main`.
- **CD for develop** (`develop.yml`): after CI, publish `X.Y.Z.devN` to TestPyPI.
- **CD for main** (`release.yml`): after CI, release-please keeps a release PR open that bumps the
  version (`pyproject.toml`, `uv.lock`) and writes `CHANGELOG.md`. Merging it tags `vX.Y.Z`,
  creates the GitHub Release, publishes to PyPI, attaches the dist files, and opens a back-merge
  PR `main` → `develop`.
- **Publishing** uses PyPI Trusted Publishing (OIDC) through GitHub environments `pypi` and
  `testpypi`, so no API token is stored.
- **Supply chain:** third-party actions are pinned to commit SHAs, and Dependabot updates them
  and the uv dependencies weekly, targeting `develop`.

## Alternatives considered
- python-semantic-release: releases straight on push with no review step. The release PR from
  release-please lets me see the next version and CHANGELOG before anything ships.
- Pure trunk-based (features straight into `main`): simpler, but I want `develop` as an
  integration and pre-release stage.
- Squash-merging `develop` → `main`: would collapse a whole release into one CHANGELOG line.
- Moderate typing (non-strict mypy): less work up front, but strict typing caught real edge cases
  (a non-object offsets file crashed the reader) and is easier to adopt while the codebase is small.

## Consequences
- Every PR title must be a Conventional Commit, and `CHANGELOG.md` and the version are never
  edited by hand.
- A release needs two merges (`develop` → `main`, then the release PR) and a back-merge afterwards.
- One-time manual setup outside the repo: PyPI/TestPyPI trusted publishers, GitHub environments,
  branch rulesets, Actions permission to open PRs, and optionally a `RELEASE_PLEASE_TOKEN` so
  release and back-merge PRs trigger CI.
- Updated: [architecture/tech-stack.md](../architecture/tech-stack.md), root `CLAUDE.md`
  (commands), `CONTRIBUTING.md`.
