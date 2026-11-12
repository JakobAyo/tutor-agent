# M5: Follow-ups and "What Just Happened"

> **Responsibility:** Follow-up questions on a lesson, and on-demand explanation of the latest agent turn.

## Goal
I can keep asking about a lesson (F9), and I can ask the tutor to explain what an agent just did and why (F8).

## Scope
- **Follow-ups:** an input field under the open lesson. Each question is a fresh call built from the lesson context, the thread so far, my known related concepts, and the question ([0012](../decisions/0012-stateless-follow-ups.md)). The thread is kept per lesson while the pane is open.
- **What just happened:** pick a session from the recently active ones, take its latest turn (including subagent work), and explain what the agent did and why, starting from the code.
- **Prompt size:** trim the oldest turns of long threads.

## Out of scope
Saving threads across restarts. Quizzes ([0006](../decisions/0006-drop-socratic-quizzes-for-now.md)).

## Done when
- [ ] Follow-up answers refer to the lesson and build on concepts I've marked `seen` or `understood`.
- [ ] No Claude Code sessions are created by follow-ups (checked in `~/.claude/projects/`).
- [ ] "What just happened" works for the latest turn of any recent session.
