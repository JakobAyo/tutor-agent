#!/usr/bin/env bash
# Spike helper: run a command without the env vars of the surrounding Claude Code
# session, so a nested `claude -p` behaves like one started from a hook in a plain shell.
exec env -u CLAUDECODE -u CLAUDE_CODE_SESSION_ID -u CLAUDE_CODE_CHILD_SESSION \
  -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_PID -u CLAUDE_CODE_MESSAGING_SOCKET \
  -u CLAUDE_CODE_MESSAGING_TOKEN -u CLAUDE_CODE_SESSION_ATTENDED -u AI_AGENT \
  -u CLAUDE_CODE_EXECPATH -u CLAUDE_EFFORT "$@"
