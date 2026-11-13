# Components

> **Responsibility:** Each component's single responsibility and its interface.

| Component | Single responsibility | Interface |
|---|---|---|
| **Hook entry** | Receive the Claude Code hook and start detection without blocking | `tutor hook`: reads the hook JSON from stdin, starts `tutor detect <transcript> --session-id <id>` detached, always exits 0 with no output ([0026](../decisions/0026-hook-handoff-and-install.md)) |
| **Transcript reader** | Turn new JSONL lines into [events](../observation/event-model.md) | `reader.read_new(transcript, session_id, advance=True) -> Batch`, keeps the last position per session and per subagent transcript ([0015](../decisions/0015-include-subagent-activity.md), [0025](../decisions/0025-byte-offsets-per-session.md)). The record mapping is in `events.py` |
| **Pre-filter** | Skip batches that can't teach anything, without an LLM call | `prefilter.skip_reason(events) -> str \| None` ([triggers](../observation/triggers.md)) |
| **Installer** | Add or remove the hook in the global Claude Code settings | `tutor install` / `tutor uninstall`: diff, confirm, backup, atomic write ([0026](../decisions/0026-hook-handoff-and-install.md)) |
| **Claude runner** | The only place that calls `claude -p` | `run(prompt, model, ...) -> text/JSON`, loads the token from the data directory's `.env` if one exists ([0019](../decisions/0019-token-in-data-directory.md)), applies the recursion guard, disables all tools and runs from the data directory ([0011](../decisions/0011-sandboxed-claude-calls.md)). The model comes from settings: cheap for detection, strong for lessons ([0016](../decisions/0016-model-per-job.md)) |
| **Detector** | Find worth-knowing concepts in a batch | `detector.detect(events, known_names, settings) -> [Candidate]`: one call on the cheap model, output validated per item, each candidate points at its event so the snippet is cut from it (`detector.snippet`, [0013](../decisions/0013-store-source-snippets.md), [0027](../decisions/0027-detection-rules.md)) |
| **Concept store** | Read and write the concept memory safely | `record(entries)` stores a detection batch in one transaction (created / attached / dismissed), plus add, list, get, set status, mark seen |
| **Notifier** | Send desktop notifications | `notifier.notify(concepts, muted=...)`: one `notify-send` per batch, only for new concepts, never raises ([0027](../decisions/0027-detection-rules.md)) |
| **Pipeline** | Run one `tutor detect` | `pipeline.process`: read → pre-filter → detect → resolve against the memory → store → notify. Every failure is logged, nothing reaches the agent session |
| **Lessons** | Write a lesson for a concept and cache it | `lessons.generate(concept, settings) -> Lesson`: one plain-text call on the strong model, built from the most recent source. `LessonCache` get/put, one file per concept ([0017](../decisions/0017-lesson-cache.md), [0028](../decisions/0028-lessons-and-tutor-pane.md)) |
| **Tutor pane** | TUI for browsing concepts and reading lessons | `tutor tui`, Textual app in `tui.py` ([0009](../decisions/0009-textual-tui.md)). Highlight shows the cached lesson or a card (no call), Enter opens (marks `seen`, generates once), `r` regenerates. Calls run in a worker thread; the concept file is polled once a second. Status keys `u`/`s`/`d`/`n`, `h` shows dismissed ([0028](../decisions/0028-lessons-and-tutor-pane.md)). `f` asks a follow-up, `w` picks a session to explain, `x` shows the last explanation ([0029](../decisions/0029-follow-ups-and-latest-turn.md)) |
| **Follow-ups** | Answer a question about an open lesson | `followups.answer(concept, lesson, thread, known, question, settings) -> str`: one call on the strong model, prompt rebuilt each time from the lesson and its source, known concepts (`known_concepts`), and the thread trimmed to the newest turns (`trim_thread`) ([0012](../decisions/0012-stateless-follow-ups.md), [0029](../decisions/0029-follow-ups-and-latest-turn.md)) |
| **Explain** | "What just happened" in a recent session | `explain.recent_sessions()`, `explain.latest_turn(session)` (last prompt to the end, plus subagent work since then), `explain.explain(turn, known, settings) -> str`: one call on the strong model. Reads transcripts only, never moves offsets. Also `tutor explain [N] [--list]` ([0029](../decisions/0029-follow-ups-and-latest-turn.md)) |

## Claude runner flags
Every call runs from the data directory with this flag set ([0022](../decisions/0022-claude-p-flag-set.md)):

```
claude -p --model <model> --output-format json \
  --tools "" --setting-sources "" --strict-mcp-config \
  --no-session-persistence --system-prompt <prompt> [--json-schema <schema>]
```

Detection passes `--json-schema` and reads the `structured_output` field ([0023](../decisions/0023-structured-detection-output.md)). With `--json-schema`, the model sees exactly one tool, `StructuredOutput`, which only returns the answer (checked in M1 by `tests/test_runner_real.py`). The prompt goes in on stdin, because `--tools` takes a variable number of values and would swallow a positional prompt.

The runner also removes the observed session's variables (`CLAUDECODE`, `CLAUDE_CODE_SESSION_ID`, …) from the environment, so the call behaves like a fresh top-level `claude -p`, the same as the M0 runs through `spike/clean_env.sh`. A timeout kills the whole process group. Any failure (exit code, non-JSON, `is_error`, missing `structured_output`) raises `ClaudeError` and is logged.

## Recursion guard
Two layers, both verified in M0 ([0022](../decisions/0022-claude-p-flag-set.md)):
1. `--setting-sources ""` loads no settings, so no hooks run for tutor calls.
2. The runner sets `TUTOR_AGENT_INTERNAL=1`. The hook entry exits at once if it sees it.

## Hook entry
- Handles `Stop` (main transcript) and `SubagentStop` (subagent transcript) ([0021](../decisions/0021-subagentstop-trigger.md)).
- Starts the detector with `subprocess.Popen(..., start_new_session=True)` and stdio set to `DEVNULL`. M0 confirmed the detector keeps running after the session exits, and that it authenticates with the existing Claude Code login.
- Keep its imports minimal: Python start-up is most of its run time. `tutor hook` skips `argparse`. Measured in M2 with the installed tool: about 35 ms including the spawn.
- The detector is started as `sys.executable -m tutor_agent.cli detect ...` from the data directory, with stderr appended to `tutor.log` ([0026](../decisions/0026-hook-handoff-and-install.md)).
