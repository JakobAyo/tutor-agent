# 0022: The exact `claude -p` flags for sandboxed calls and the recursion guard

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
[0011](0011-sandboxed-claude-calls.md) requires tool-less calls from a neutral directory. [0003](0003-claude-p-subscription-runtime.md) requires that tutor calls never fire the tutor's own hook. The M0 spike (`spike/sandbox_test.sh`, Claude Code 2.1.322) tested flag sets against a project that has hooks and a marker `CLAUDE.md`:

| Flags | Hooks fired | `CLAUDE.md` loaded | Tools available | Input tokens |
|---|---|---|---|---|
| none | yes | yes | all, plus claude.ai MCP connectors | ~31k |
| `--tools ""` | yes | no | claude.ai MCP connectors still present | ~90k |
| `--tools "" --setting-sources ""` | no | no | none | ~3.6k |
| `--tools "" --safe-mode` | no | no | none | ~2.9k |
| final set (below) | no | no | none | ~0.7k |

`--bare` would skip hooks and `CLAUDE.md` too, but it only authenticates with `ANTHROPIC_API_KEY`. It can't use the subscription.

## Decision
Every tutor call uses this flag set, run with `cwd` = the tutor data directory:

```
claude -p --model <model> --output-format json \
  --tools "" --setting-sources "" --strict-mcp-config \
  --no-session-persistence --system-prompt <prompt>
```

- `--tools ""` removes built-in tools. `--strict-mcp-config` removes MCP servers.
- `--setting-sources ""` skips user, project, and local settings, so **no hooks and no plugins load**. This is the main recursion guard.
- `--no-session-persistence` keeps tutor calls out of `~/.claude/projects`, so they never appear as transcripts.
- `--system-prompt` replaces the Claude Code system prompt, which cuts input tokens from ~3.6k to ~0.7k.
- The runner also sets `TUTOR_AGENT_INTERNAL=1`. The hook entry exits at once if it sees it. The spike confirmed the variable reaches hooks, so it is a second guard in case a future CLI version loads hooks anyway.

## Alternatives considered
- `--safe-mode`: also works, but it is described as a troubleshooting mode and may change meaning. `--setting-sources` states exactly what we want.
- `--bare`: no OAuth, see above.
- Environment-variable guard only: the hook process would still start for every tutor call.

## Consequences
- Tutor calls are cheap, side-effect free, and invisible to the observer.
- Settings such as `model` and `effortLevel` from my user settings don't apply. The runner passes `--model` itself.
- Updated: [architecture/components.md](../architecture/components.md), [architecture/tech-stack.md](../architecture/tech-stack.md), [requirements/non-functional.md](../requirements/non-functional.md).
