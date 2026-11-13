# Tutor Agent

A personal tutor agent. It watches my Claude Code sessions and teaches me the concepts behind what the agents are doing. The goal is to reach senior-SWE-level understanding faster, and to stop being a "vibe coder" who ships code they can't explain.

## Core idea
- **Observe:** a Claude Code hook fires at the end of each agent turn. The tutor reads the new part of the session transcript (code, commands, reasoning).
- **Detect:** in the background, find concepts that are new to me and worth knowing (patterns, architecture, mechanisms, trade-offs, not syntax). Store them in a global concept memory and send a desktop notification.
- **Teach on demand:** in a separate terminal pane, explain a concept starting from the real code where it appeared, then generalize, and give links for further reading. Explain *why* the agent did something, not only *what* it did.
- **Track progress:** each concept has a status `new` → `seen` → `understood`. I mark `understood` myself, or `dismissed` if it's not worth learning.

## Principles
- The goal is learning, not output. The tutor explains. It does not write code for me.
- Never block or change the observed agent session.
- Tie every lesson to the real code, then generalize.
- Keep it short. Skip basics: I have a CS background but little practical experience.

## Status
Design phase, no code yet. Decided: Claude Code only (all sessions, including subagents), `claude -p` on my subscription (no tools, neutral directory, cheap model for detection), source snippets stored with each concept, Python 3.12+ with uv, global status-based memory in one JSON file, Textual TUI, cached lessons, stateless follow-ups, token (if needed) in the data directory, no quizzes for now (see `docs/decisions/`). Milestones are planned in `docs/milestones/` (M0 spike to M6 daily use). M0 spike done (results in `docs/milestones/m0-spike.md`, ADRs 0021–0023, throwaway scripts in `spike/`). M1 foundation done: package `src/tutor_agent/` (paths, settings, log, store, runner, CLI stubs), settings in `settings.toml` (ADR 0024). M2 observation pipeline done (hook, reader with byte offsets per session, pre-filter, `tutor install`; ADRs 0025–0026), checked in real sessions including background subagents (see `docs/milestones/m2-observation.md`). M3 detection implemented (detector, notifier, `ConceptStore.record`; ADR 0027), prompt tests pass on the M0 fixtures. M4 tutor pane done (`tutor tui`, lessons with cache; ADR 0028). M5 done: follow-ups under a lesson and "what just happened" for a recent session (`followups.py`, `explain.py`, `tutor explain`; ADR 0029). M6 (daily use and tuning) in progress: first round done (snippets point at code and lessons teach from the best code source, ADR 0030; usage ledger and `tutor stats`, ADR 0031). Round two: detections run one at a time so KNOWN is always current (ADR 0032). Next: real daily use, logged in `docs/milestones/m6-daily-use.md`.

## Commands
- `uv sync`: set up the dev environment.
- `uv run pytest`: offline tests (a fake `claude`, no usage spent).
- `uv run pytest -m real`: the one real `claude -p` call (Haiku, about $0.001).
- `uv run pytest -m prompt`: detection quality on the five M0 fixtures plus one real M6 batch (7 Haiku calls, about $0.05), lesson quality (1 Sonnet call), and follow-up and explanation quality (2 Sonnet calls).
- `tutor tui`: the tutor pane (Enter opens a lesson, `u`/`s`/`d`/`n` change status, `r` regenerates, `h` shows dismissed, `f` asks a follow-up, `w` explains a recent session's latest turn, `x` shows it again).
- `tutor stats [--days N]`: concept memory size and model usage per day (no call).
- `tutor explain [N] [--list]`: explain what just happened in recent session N (default: the most recent), one Sonnet call; `--list` makes no call.
- `uv tool install --force --reinstall .`: install or refresh the `tutor` command (without `--reinstall`, uv may keep a stale build of the same version).
- `tutor install` / `tutor uninstall`: add or remove the hook in `~/.claude/settings.json` (shows a diff, asks, backs up).
- `tutor detect <transcript.jsonl> --dry-run`: log the next batch to `~/.local/share/tutor-agent/tutor.log` without moving the offset.

## Docs
All project decisions and design notes live in `docs/`. Start at `docs/CLAUDE.md` (index).
- Record each significant decision as a new ADR in `docs/decisions/`, using the template there.
- One responsibility per folder and one topic per file. When a file starts covering two things, split it.
