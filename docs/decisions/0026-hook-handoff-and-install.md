# 0026: The hook hands off by transcript path and is installed by absolute path

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
The hook runs inside every agent turn. It must start `tutor detect` quickly and without depending on the observed session's `PATH` or working directory, and a crash anywhere after it must not reach the session. `tutor install` edits my global `~/.claude/settings.json`, which also holds unrelated settings and hooks.

## Decision
- **Handoff:** the hook passes only `tutor detect <transcript> --session-id <id>`. `Stop` passes `transcript_path`, `SubagentStop` passes `agent_transcript_path` ([0021](0021-subagentstop-trigger.md)). Everything else (agent id, cwd, timestamps) comes from the transcript records.
- **Start:** `sys.executable -m tutor_agent.cli detect ...`, so it uses the same Python and package as the hook. `cwd` is the data directory, stdin and stdout are `/dev/null`, `start_new_session=True`, and stderr is appended to `tutor.log`, so even an import error lands there.
- **Hook process:** `tutor hook` skips `argparse`, catches every exception, logs it, and always exits 0 with no output.
- **Install:** the settings get one `Stop` and one `SubagentStop` entry whose command is the absolute path of `tutor` plus `hook`, with a 10 s timeout. `tutor install` and `uninstall` show a diff, ask (`--yes` skips the question), back up the old file as `settings.json.tutor-backup-<time>`, and replace it atomically. They only touch entries whose command ends in `tutor hook`. `CLAUDE_CONFIG_DIR` is honoured.

## Alternatives considered
- Pass the whole hook payload (environment variable or temp file): more moving parts, and the transcript has all the data.
- `tutor` from `PATH` in the hook command: the hook environment's `PATH` isn't guaranteed to include `~/.local/bin`.
- Write a separate hooks file: Claude Code reads hooks only from its settings files.

## Consequences
- The hook takes about 35 ms, with Python start-up as most of it (measured in M2).
- Running `tutor detect <transcript> --dry-run` by hand reproduces exactly what the hook would start.
- After reinstalling with the same version, `uv tool install --force .` may keep a stale cached build. Use `--reinstall`.
- Updated: [architecture/components.md](../architecture/components.md).
