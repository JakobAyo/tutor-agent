# Contributing

Thanks for helping! This page covers the dev setup, the branch flow, and how releases happen.

## Dev setup

```sh
uv sync                                                        # venv + all dev tools from uv.lock
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
```

The quality gates (CI runs exactly these; all must pass):

```sh
uv run ruff check                    # lint
uv run ruff format --check           # formatting (run without --check to fix)
uv run mypy                          # strict type check of src/
uv run mypy tests --allow-untyped-defs --allow-incomplete-defs --allow-untyped-calls --check-untyped-defs
uv run pytest --cov                  # offline tests, coverage must stay >= 90%
```

The offline tests use a fake `claude` binary and spend nothing. Two opt-in suites call the real
model on your subscription: `uv run pytest -m real` (one Haiku call) and `uv run pytest -m prompt`
(prompt-quality checks, about $0.05). CI never runs them.

## Branch flow

```
feature/*, fix/* ──squash──▶ develop ──merge commit──▶ main ──▶ release PR ──▶ vX.Y.Z
                               │                         ▲
                               └─ TestPyPI .devN build    └─ hotfix/* (rare)
```

1. Branch off `develop` (`feat/…`, `fix/…`, `docs/…`).
2. Open a PR into **`develop`**. The **PR title must be a [Conventional Commit](https://www.conventionalcommits.org/)**
   (`feat: add quiz mode`, `fix(reader): handle truncated lines`). PRs are **squash-merged**, so
   the title becomes the commit message that drives versioning and the CHANGELOG.
3. Every merge into `develop` publishes a pre-release (`X.Y.Z.devN`) to TestPyPI.
4. To ship, open a PR **`develop` → `main`** and merge it with a **merge commit** (not squash), so
   each change keeps its own line in the CHANGELOG.
5. release-please then opens a **release PR** on `main` (version bump + CHANGELOG). Merging it
   tags `vX.Y.Z`, creates the GitHub Release, publishes to PyPI, and opens a back-merge PR
   `main` → `develop`. Merge that one with a merge commit as well.

Only `develop`, `release-please--*` and `hotfix/*` branches may target `main`.

## Commit types and what they do to the version

While the version is `0.x`, breaking changes bump the minor version instead of the major one.

| Type | Meaning | Version bump | In CHANGELOG |
|---|---|---|---|
| `feat` | new user-facing capability | minor | Features |
| `fix` | bug fix | patch | Bug Fixes |
| `perf` | faster, same behaviour | patch | Performance |
| `deps` | runtime dependency update | patch | Dependencies |
| `refactor`, `docs` | no behaviour change | none | yes |
| `test`, `build`, `ci`, `style`, `chore` | internal | none | hidden |
| `feat!` / `BREAKING CHANGE:` footer | breaking change | major (minor while `0.x`) | flagged |

Never edit `CHANGELOG.md` or the version in `pyproject.toml` by hand; release-please owns both.

## Design decisions

Significant decisions are recorded as ADRs in [`docs/decisions/`](docs/decisions/) using the
template there. If your change makes a new decision, add an ADR in the same PR.
