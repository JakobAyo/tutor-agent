# M6: Daily Use and Tuning

> **Responsibility:** Run the tutor in real daily work, tune it, and check it against the goals.

## Goal
The tutor runs in all my sessions for two weeks, and I fix whatever stops it from being useful.

## Scope
- Keep a short issue log during use: missed concepts, noise, bad lessons, slow spots, crashes.
- Tune the detection and lesson prompts against that log. Switch the detection model if quality is too low ([0016](../decisions/0016-model-per-job.md)).
- Check the size of the concept memory and the usage per day.
- Record lasting design changes as ADRs.

## Done when
- [ ] Two weeks of use with no tutor problem ever showing up in an agent session.
- [ ] Notifications feel useful, not noisy (most detected concepts are ones I want to learn).
- [ ] Each [goal](../vision/goals.md) is reviewed: what works and what's missing.
- [ ] The next round of work (for example quizzes or a project filter) is listed as candidate ADRs.

## Log

### 2026-11-13: first real detection (M3 day of real use, start)
Session: tutor-agent development, transcript lines 52–75 (no code edits, chat plus shell output). One Haiku call, ~10 s, ~$0.0013.

Detected: "Lifecycle hooks", "Installed artifact vs source checkout", "Incremental processing with offset checkpoints".

- **Good:** all three are real concepts from the turn, no basics. Categories and summaries are general, and the `context` line says why each one appeared.
- **Snippet is prose, not code:** two concepts share the same snippet (the whole previous assistant answer), and the third is grep and log output with a 649-character cut in the middle. A lesson built on these would quote chat text, not code. Expected on a turn without code edits; recheck on code-heavy turns, and if the snippet is still prose there, revisit snippet choice ([0027](../decisions/0027-detection-rules.md)).
- **Summary slightly wrong:** "Incremental processing with offset checkpoints" says "line numbers in a transcript", but the reader stores byte offsets. Haiku inferred line numbers from the log text `lines 44-51`.
- **Bias:** the session observed was the tutor's own development, so the concepts are about the tutor. Sessions in other projects are a better test.

Still to check: near-duplicates over the day, snippets on code-heavy turns.

### 2026-11-13: first real lesson (M4)
Lesson for "Installed artifact vs source checkout" (Sonnet, one call). The general concept, trade-offs and links read well. "What the agent did" quoted a line of chat text, because the concept's most recent source was an assistant summary, and the "why" part then guessed at a story around it. Same root cause as the prose-snippet finding above.

Still to check: whether the lesson links exist (the model has no tools to check them).

### 2026-11-13: first real "what just happened" (M5)
`tutor explain` on a short `metris-builder-delta` turn (one `xdg-open` command). Correct and honest: it said the `started` output doesn't prove the browser opened, and that the page description came from earlier work it couldn't see. But it explained `&` and `>/dev/null 2>&1`, which are basics. Watch whether "skip basics" needs a stronger line in the explanation prompt, or whether short turns are just thin material.

### 2026-11-13: snippets on code-heavy turns (round 1 of tuning)
Checked the 13 concepts stored on day one. Code-heavy turns did not fix the snippets: three concepts shared one `git commit` message, three shared a final summary, "Atomic file replacement" pointed at `cat` output, and "Lazy import" at a test diff instead of the `cli.py` edit. Lessons made it worse by always taking the newest source, which is usually a commit or a summary.

Fix ([0030](../decisions/0030-snippets-show-code.md)): the detection prompt now says to point at the event where the concept is implemented, sources store their event kind, and lessons teach from the newest source that shows the most code. The real batch (lines 153–451) is now a `prompt` test fixture. Re-run: Haiku picked the `tui.py` and `lessons.py` edits and `cat` output of `store.py`, no prose.

Usage tracking added ([0031](../decisions/0031-usage-ledger.md)): `tutor stats` shows memory size and calls/cost per day. Day one from the log, before the ledger: 10 Haiku detection calls, about $0.017; 1 Sonnet lesson, $0.015. Memory: 13 concepts, 24 sources, 46 KB.

Still to check: the snippet choice over more turns and other projects; whether cached lessons built on prose should be regenerated (`r`).
