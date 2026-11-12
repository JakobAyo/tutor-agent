# Components

> **Responsibility:** Each component's single responsibility and its interface.

| Component | Single responsibility | Interface |
|---|---|---|
| **Hook entry** | Receive the Claude Code hook and start detection without blocking | Reads the hook JSON from stdin, starts the detector detached, exits 0 |
| **Transcript reader** | Turn new JSONL lines into [events](../observation/event-model.md) | `read_new(session) -> batch`, keeps the last position per session and per subagent transcript ([0015](../decisions/0015-include-subagent-activity.md)) |
| **Claude runner** | The only place that calls `claude -p` | `run(prompt, model, ...) -> text/JSON`, loads the token from the data directory's `.env` if one exists ([0019](../decisions/0019-token-in-data-directory.md)), applies the recursion guard, disables all tools and runs from the data directory ([0011](../decisions/0011-sandboxed-claude-calls.md)). The model comes from settings: cheap for detection, strong for lessons ([0016](../decisions/0016-model-per-job.md)) |
| **Detector** | Find worth-knowing concepts in a batch | `detect(batch, known_names) -> [concept]`, each with a short source snippet ([0013](../decisions/0013-store-source-snippets.md)) |
| **Concept store** | Read and write the concept memory safely | add, update status, list, add source |
| **Notifier** | Send desktop notifications | `notify(concepts)` through `notify-send` |
| **Tutor pane** | TUI for browsing concepts and reading lessons | Textual app ([0009](../decisions/0009-textual-tui.md)), uses the store and the runner. Shows cached lessons and regenerates them only on request ([0017](../decisions/0017-lesson-cache.md)). Keeps the follow-up thread per lesson and rebuilds the full prompt on every question ([0012](../decisions/0012-stateless-follow-ups.md)) |

## Claude runner flags
Every call runs from the data directory with this flag set ([0022](../decisions/0022-claude-p-flag-set.md)):

```
claude -p --model <model> --output-format json \
  --tools "" --setting-sources "" --strict-mcp-config \
  --no-session-persistence --system-prompt <prompt> [--json-schema <schema>]
```

Detection passes `--json-schema` and reads the `structured_output` field ([0023](../decisions/0023-structured-detection-output.md)). The prompt goes in on stdin, because `--tools` takes a variable number of values and would swallow a positional prompt.

## Recursion guard
Two layers, both verified in M0 ([0022](../decisions/0022-claude-p-flag-set.md)):
1. `--setting-sources ""` loads no settings, so no hooks run for tutor calls.
2. The runner sets `TUTOR_AGENT_INTERNAL=1`. The hook entry exits at once if it sees it.

## Hook entry
- Handles `Stop` (main transcript) and `SubagentStop` (subagent transcript) ([0021](../decisions/0021-subagentstop-trigger.md)).
- Starts the detector with `subprocess.Popen(..., start_new_session=True)` and stdio set to `DEVNULL`. M0 confirmed the detector keeps running after the session exits, and that it authenticates with the existing Claude Code login.
- Keep its imports minimal: Python start-up is most of its run time.
