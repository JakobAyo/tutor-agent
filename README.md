# tutor-agent

[![CI](https://github.com/JakobAyo/tutor-agent/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/JakobAyo/tutor-agent/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/tutor-agent)](https://pypi.org/project/tutor-agent/)
[![Python](https://img.shields.io/pypi/pyversions/tutor-agent)](https://pypi.org/project/tutor-agent/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A tutor that watches your Claude Code sessions and teaches you the concepts behind what the agent just did.**

Coding agents write code faster than you can learn from it. `tutor-agent` runs quietly next to
them. At the end of each agent turn it reads what happened, spots concepts that are new to *you*
(patterns, architecture, mechanisms, trade-offs, not syntax) and sends a desktop notification.
When you have a minute, open the tutor pane: each lesson starts from the real code where the
concept appeared, then generalizes, explaining *why* the agent did it and not only *what*.

It never blocks or changes your agent session, and it never writes code for you.

## How it works

1. **Observe:** a Claude Code `Stop` / `SubagentStop` hook fires after each agent turn and hands
   the new part of the session transcript to a detached background process.
2. **Detect:** a cheap model (Haiku class) picks out concepts worth learning and stores them in a
   local concept memory (`~/.local/share/tutor-agent/`), with the code snippet where each appeared.
3. **Teach on demand:** `tutor tui` opens a terminal pane. Pick a concept to get a lesson from a
   stronger model, ask follow-ups, or ask "what just happened?" about a recent session.
4. **Track progress:** each concept moves `new` → `seen` → `understood` (or `dismissed`).

All model calls go through `claude -p` on your existing Claude Code login, sandboxed: no tools,
no MCP servers, no session persistence.

## Requirements

- Linux (notifications use `notify-send`)
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- [Claude Code](https://docs.claude.com/en/docs/claude-code), installed and logged in

## Install

```sh
uv tool install tutor-agent
tutor install          # adds the hook to ~/.claude/settings.json (shows a diff, asks, backs up)
```

Remove the hook with `tutor uninstall`.

## Usage

| Command | What it does |
|---|---|
| `tutor tui` | The tutor pane. `Enter` opens a lesson, `u`/`s`/`d`/`n` change status, `r` regenerates, `f` asks a follow-up, `w` explains a recent session, `h` shows dismissed. |
| `tutor explain [N] [--list]` | Explain the latest turn of recent session N (one model call). `--list` makes no call. |
| `tutor stats [--days N]` | Concept memory size and model usage per day (no call). |
| `tutor detect <transcript.jsonl> --dry-run` | Log the next batch without detecting, for debugging. |

Settings (models, timeouts, mute) live in `~/.local/share/tutor-agent/settings.toml`.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the dev setup, the branch
flow, and how releases work. Design decisions are recorded as ADRs in
[`docs/decisions/`](docs/decisions/).

## License

[MIT](LICENSE)
