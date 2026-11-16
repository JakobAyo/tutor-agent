# 0034: Secret and private-data scanning

- **Status:** Accepted
- **Date:** 2026-11-16

## Context
The repo is public and much of the code will be written by LLM agents. The tutor's input is real
Claude Code transcripts, so test fixtures, spike results and docs can easily pick up a home
directory, a Claude project slug (`-home-<name>-…`), an email, a name or an employer. This
already happened once and was cleaned up by hand (commit `cdb168a`). Generic secret scanners only
look for credentials, not for this kind of personal data.

## Decision
- **GitHub secret scanning + push protection** stay on (the default for public repos). The
  generic-pattern and validity-check options aren't available on this repo, so gitleaks covers
  generic patterns.
- **gitleaks** runs in CI on the *full git history* and the working tree (a checksum-verified
  binary, `--redact`), and as a pre-commit hook on staged changes.
- **`scripts/check_private_data.py`** (stdlib only) checks every tracked file, fixtures included,
  for home paths, project slugs, emails outside noreply/example domains, and private terms. The
  terms come from the untracked `.private-terms` file locally and the optional `PRIVATE_TERMS`
  repo secret in CI. It runs in CI (part of "CI passed") and as a pre-commit hook. Placeholders
  `/home/u`, `/home/me`, `-home-u-` and `someone@example.com` are allowed, and a line can opt out
  with `private-data: allow`.
- All findings are printed **redacted**, because CI logs of a public repo are public.

## Alternatives considered
- Only gitleaks with custom rules: possible, but private terms would have to sit in a committed
  config file, which leaks them by itself.
- Scanning only the PR diff: misses data that is already in the tree. The repo is small, so
  scanning everything is fast.

## Consequences
- Tests that need real-looking values build them by concatenation (see
  `tests/test_check_private_data.py`).
- The pre-commit privacy hooks don't skip `spike/` and `tests/fixtures/`, unlike the whitespace fixers.
- Updated: [architecture/tech-stack.md](../architecture/tech-stack.md), `CONTRIBUTING.md`,
  `SECURITY.md`.
