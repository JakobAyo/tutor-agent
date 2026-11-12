# 0019: The auth token lives in the tutor data directory

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
[0003](0003-claude-p-subscription-runtime.md) put the `claude setup-token` token in `.env` in the tutor repo. But the CLI is installed with `uv tool install` ([0010](0010-uv-and-python-312.md)), and the hook runs it from any project directory, so the installed tool can't reliably find the repo's `.env`. It's also not certain that a token is needed at all. A plain `claude -p` may already use the credentials of my logged-in Claude Code.

## Decision
- This changes where 0003 stores the token. Everything else in 0003 still holds.
- If a token is needed, it lives in `~/.local/share/tutor-agent/.env`, with file permissions `600`.
- The Claude runner loads it from there and passes it to `claude -p` as an environment variable. If the file doesn't exist, the runner relies on the existing Claude Code login.
- The spike checks whether `claude -p` started from the hook works without a token. If it does, the token is optional.

## Alternatives considered
- Keep `.env` in the repo and find it through an environment variable: one more setting to keep in sync, and it breaks if the repo moves.
- The system keyring: more secure, but it needs an extra dependency and has to work from a detached background process.

## Consequences
- The installed tool finds the token from any working directory.
- The tutor repo holds no secrets, so there's no `.env` in it to leak.
- Updated: [architecture/data-storage.md](../architecture/data-storage.md), [architecture/components.md](../architecture/components.md), [architecture/tech-stack.md](../architecture/tech-stack.md), [requirements/non-functional.md](../requirements/non-functional.md).
