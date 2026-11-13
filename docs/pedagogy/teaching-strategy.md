# Teaching Strategy

> **Responsibility:** Teaching methods (Socratic questioning, predict-the-next-step, spaced repetition) and when to use each.

Current method: **explain from real code, then point to further reading** ([0006](../decisions/0006-drop-socratic-quizzes-for-now.md)).

## Lesson structure
1. **What the agent did:** the actual snippet or command, quoted from the snippet stored with the source reference (the most recent source that shows code: an edit beats a command or its output, which beats prose, [0013](../decisions/0013-store-source-snippets.md), [0030](../decisions/0030-snippets-show-code.md)).
2. **Why it did it:** the problem this concept solves here.
3. **The general concept:** what it is beyond this case, in plain terms.
4. **Trade-offs:** when *not* to use it, and the common alternatives.
5. **Read more:** 2–3 good links (official docs, well-known articles, book chapters).

## Style
- Short and concrete. Start from the code, not the theory.
- Assume a CS background: skip basics, but explain practical "why" and "how in real projects".
- Follow-up questions are answered in the context of the same lesson. Each answer is built from the lesson context, the thread so far, and related concepts I've already `seen` or `understood`, so it builds on what I know ([0012](../decisions/0012-stateless-follow-ups.md)). Long threads lose their oldest turns ([0029](../decisions/0029-follow-ups-and-latest-turn.md)).

## What just happened
On demand, the latest turn of a chosen session is explained in four parts: what happened (steps, quoting code and commands), why it did it this way (decisions, alternatives, costs), concepts behind it (known ones only named), and worth checking (what a senior engineer would question). Not cached ([0029](../decisions/0029-follow-ups-and-latest-turn.md)).

## Not used for now
Socratic questioning, predict-the-next-step, and spaced repetition. They can be added later through a new ADR.
