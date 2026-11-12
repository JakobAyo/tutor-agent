# Tutor Agent

A personal tutor agent. It watches my other coding agents while they work and teaches me the concepts behind what they're doing. The goal is to reach senior-SWE-level understanding faster, and to stop being a "vibe coder" who ships code they can't explain.

## Core idea
- **Observe:** follow the sessions of other coding agents (the code they write, the commands they run, the decisions they make).
- **Teach:** explain the concepts underneath: language features, design patterns, architecture, testing, tooling, trade-offs. Explain *why* the agent did something, not only *what* it did.
- **Check understanding:** ask questions, give small exercises, and get me to predict or critique the agent's next step before it happens.
- **Track progress:** keep a model of what I know and where my gaps are, and adjust depth and topics to fit.

## Principles
- The goal is learning, not output. The tutor explains and asks questions. It does not write code for me.
- Prefer Socratic questioning and active recall over long lectures.
- Tie every lesson to the real code being written right now, then generalize.
- Keep it short and timely: teach at the moment the concept shows up.

## Status
Early design phase. No code yet. Tech stack, the mechanism for observing agents, and storage are undecided (see `docs/decisions/`).

## Docs
All project decisions and design notes live in `docs/`. Start at `docs/CLAUDE.md` (index).
- Record each significant decision as a new ADR in `docs/decisions/`, using the template there.
- One responsibility per folder and one topic per file. When a file starts covering two things, split it.
