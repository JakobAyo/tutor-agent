# Tech Stack

> **Responsibility:** Languages, frameworks, models, and tools in use, with versions.

| Area | Choice | Decision |
|---|---|---|
| Language | Python 3.12+ | [0004](../decisions/0004-python.md), [0010](../decisions/0010-uv-and-python-312.md) |
| LLM access | `claude -p` (headless Claude Code CLI) on my subscription | [0003](../decisions/0003-claude-p-subscription-runtime.md) |
| Models | Cheap model (Haiku class) for detection, strong model (Sonnet/Opus class) for lessons and follow-ups, both set in settings | [0016](../decisions/0016-model-per-job.md) |
| Auth | Existing Claude Code login (works from a detached hook process, verified in M0). A `claude setup-token` token in the data directory's `.env` is optional | [0003](../decisions/0003-claude-p-subscription-runtime.md), [0019](../decisions/0019-token-in-data-directory.md) |
| Observation | Claude Code `Stop` and `SubagentStop` hooks + JSONL transcripts (verified on Claude Code 2.1.322) | [0002](../decisions/0002-observe-claude-code-only.md), [0021](../decisions/0021-subagentstop-trigger.md) |
| Notifications | `notify-send` (Linux) | [0007](../decisions/0007-interaction-model.md) |
| LLM sandboxing | `claude -p --tools "" --setting-sources "" --strict-mcp-config --no-session-persistence --system-prompt …`, run from the data directory | [0011](../decisions/0011-sandboxed-claude-calls.md), [0022](../decisions/0022-claude-p-flag-set.md) |
| Structured output | `--json-schema`, read from `structured_output` | [0023](../decisions/0023-structured-detection-output.md) |
| Concept memory | One JSON file in `~/.local/share/tutor-agent/` | [0008](../decisions/0008-concept-memory-json.md) |
| TUI | Textual 8.2 (the only runtime dependency, imported only by `tutor tui`) | [0009](../decisions/0009-textual-tui.md), [0028](../decisions/0028-lessons-and-tutor-pane.md) |
| Packaging/tooling | uv (`uv_build` backend, `src/` layout), installed with `uv tool install .` | [0010](../decisions/0010-uv-and-python-312.md) |
| Settings | `settings.toml` in the data directory, read with `tomllib` | [0024](../decisions/0024-settings-toml.md) |
| Tests | pytest + pytest-cov (90% branch-coverage floor). A fake `claude` binary for runner tests; the one real call is opt-in (`uv run pytest -m real`) | M1, [0033](../decisions/0033-ci-cd-and-release-automation.md) |
| Code quality | ruff (lint + format), mypy `--strict` on `src/`, pre-commit hooks | [0033](../decisions/0033-ci-cd-and-release-automation.md) |
| CI/CD | GitHub Actions: `ci.yml` (gates on PRs), `develop.yml` (TestPyPI `.devN`), `release.yml` (release-please → PyPI), CodeQL, Dependabot | [0033](../decisions/0033-ci-cd-and-release-automation.md) |
| Secrets & privacy | GitHub secret scanning + push protection, gitleaks (CI over full history + pre-commit), `scripts/check_private_data.py` (home paths, project slugs, emails, private terms) | [0034](../decisions/0034-secret-and-private-data-scanning.md) |
| Versioning | SemVer from Conventional Commits via release-please; it owns `CHANGELOG.md` and the version | [0033](../decisions/0033-ci-cd-and-release-automation.md) |
| License | MIT | [0033](../decisions/0033-ci-cd-and-release-automation.md) |
