# 0029: Follow-up prompts, thread trimming, and "what just happened"

- **Status:** Accepted
- **Date:** 2026-11-13

## Context
M5 builds follow-up questions (F9) and "explain what just happened" (F8). [0012](0012-stateless-follow-ups.md) says each follow-up rebuilds its context, but not which "related" concepts go in, how long threads are trimmed, or what "the latest turn" of a session is and how it is found.

## Decision
- **Follow-up call:** one plain-text call on `lesson_model` ([0016](0016-model-per-job.md)). The prompt holds the concept, the **source the cached lesson was built from** (snippet in a safe fence), the lesson text, what I know, the thread, and the question. Follow-ups need a cached lesson: without one there is nothing to refer to.
- **What I know:** every `seen` or `understood` concept except the lesson's own, most recently updated first, at most 40, as name, status and summary. The model picks what is related. No similarity search.
- **Thread:** kept per concept in the pane's memory while it runs, not saved. The prompt keeps the newest turns that fit in 12,000 chars and says how many older ones were left out. The newest turn is always kept. A failed answer is not added to the thread, and the question goes back into the input.
- **Recent sessions:** the 10 main transcripts in `~/.claude/projects/*/*.jsonl` (or `$CLAUDE_CONFIG_DIR/projects`) with the newest mtime, counting their subagent transcripts. Each is labelled with its project and last prompt, read from the file's end (256 KB, growing up to 8 MB until a prompt shows up).
- **Latest turn:** from the last real prompt in the main transcript (injected wrappers such as `<task-notification>` don't count) to the end, plus records of the session's subagent transcripts with a timestamp at or after that prompt, merged by time. Events are mapped with the same `EventMapper` as detection. The prompt and the newest events that fit in 40,000 chars (at most 150 events) are kept. Offsets are never read or moved: this is independent of detection.
- **Explanation call:** one plain-text call on `lesson_model` with what I know and the turn's events (subagent events marked). Sections: what happened, why it did it this way, concepts behind it, worth checking. Not cached and not stored as concepts.
- **Pane:** `f` focuses the follow-up input under the lesson, Esc goes back to the list. `w` opens a session picker, `x` shows the last explanation again. Moving in the concept list leaves the explanation; a reload by the poll does not. `tutor explain [N] [--list]` does the same from the shell.

## Alternatives considered
- Pick related concepts by category or by word overlap: cheap, but misses links across categories. 40 one-line summaries are small next to the lesson.
- Trim threads by summarizing old turns: one more call per question.
- Latest turn = the last detection batch (offsets): it would depend on what the detector already read, and would miss a turn the pre-filter skipped.
- Find the session by the current directory: the pane runs in its own terminal, often in another directory.

## Consequences
- No Claude Code session is created by follow-ups or explanations: same flag set as all calls ([0022](0022-claude-p-flag-set.md)), checked by `tests/test_followup_prompt.py`.
- Threads are lost when the pane closes (out of scope for M5).
- Very long turns lose their oldest work; the explanation then says so.
- Updated: [architecture/components.md](../architecture/components.md), [architecture/overview.md](../architecture/overview.md), [pedagogy/teaching-strategy.md](../pedagogy/teaching-strategy.md), [architecture/data-storage.md](../architecture/data-storage.md).
