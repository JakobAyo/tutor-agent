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
- [x] Follow-up answers refer to the lesson and build on concepts I've marked `seen` or `understood`.
- [x] No Claude Code sessions are created by follow-ups (checked in `~/.claude/projects/`).
- [x] "What just happened" works for the latest turn of any recent session.

## Results (2026-11-13)
Decision: [0029](../decisions/0029-follow-ups-and-latest-turn.md) (follow-up prompt, known concepts, thread trimming, recent sessions, latest turn, explanation call, keys).

| Item | Evidence |
|---|---|
| Follow-ups refer to the lesson and known concepts | `uv run pytest -m prompt tests/test_followup_prompt.py` (one Sonnet call): the answer talks about the supervisor and uses the `understood` concept "Process groups". Offline, `tests/test_tui.py` checks the prompt holds the lesson, known concepts and the thread, threads are per lesson, and status keys type into the input |
| No sessions created | The same test compares `~/.claude/projects/**/*.jsonl` before and after the call. After real `tutor explain` runs, no project folder exists for the data directory |
| Any recent session | `tests/test_explain.py`: last prompt to the end, injected wrappers don't start a turn, subagent work from the same span is merged by time, long turns keep the prompt and the newest events. Real: `tutor explain 4` on a `metris-builder-delta` session (~10 s, one Sonnet call) gave a correct four-part explanation; the session picker labels all 10 recent sessions, including a 1 MB transcript whose prompt is far back |
| Offline tests | `uv run pytest`: 177 tests |

Not checked: how useful explanations are over many turns (M6).
