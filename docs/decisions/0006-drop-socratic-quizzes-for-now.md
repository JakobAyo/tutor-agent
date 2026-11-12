# 0006: Drop Socratic questioning and quizzes for now

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
The original principles in the root `CLAUDE.md` called for Socratic questioning, active recall, and predicting the agent's next step. My actual need right now is different: I know the CS theory, but I meet many concepts in practice that I don't understand, and I want to **read about and understand** them when they come up.

## Decision
- Lessons are explanations tied to the real code, plus links for further reading.
- No quizzes, prediction exercises, or spaced repetition for now.
- The Socratic principle and the "check understanding" goal are removed from the root `CLAUDE.md`.

## Alternatives considered
- Keep Socratic questioning as the default: stronger for retention, but it adds friction I don't want right now.
- Offer quizzes only on request: deferred, and easy to add later as a new ADR.

## Consequences
- Lessons are faster and less tiring, but retention is weaker. The only progress signal is my own `understood` mark.
- Updated: root `CLAUDE.md`, [pedagogy/teaching-strategy.md](../pedagogy/teaching-strategy.md), [pedagogy/assessment.md](../pedagogy/assessment.md).
