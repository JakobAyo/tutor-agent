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
Design phase, no code yet. Decided: Claude Code only (all sessions, including subagents), `claude -p` on my subscription (no tools, neutral directory, cheap model for detection), source snippets stored with each concept, Python 3.12+ with uv, global status-based memory in one JSON file, Textual TUI, cached lessons, stateless follow-ups, token (if needed) in the data directory, no quizzes for now (see `docs/decisions/`). Milestones are planned in `docs/milestones/` (M0 spike to M6 daily use). Next: M0 spike.

## Docs
All project decisions and design notes live in `docs/`. Start at `docs/CLAUDE.md` (index).
- Record each significant decision as a new ADR in `docs/decisions/`, using the template there.
- One responsibility per folder and one topic per file. When a file starts covering two things, split it.
