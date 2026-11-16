#!/usr/bin/env bash
# Spike Q3/Q4: which flag set gives a tool-less, hook-less, CLAUDE.md-free `claude -p`?
# Usage: sandbox_test.sh <project-dir-with-hooks-and-marker-CLAUDE.md> <hook-log>
# Prints per variant: hook lines added, whether the CLAUDE.md marker leaked, tools seen, input tokens.
set -u
proj=$1; log=$2; here=$(dirname "$(realpath "$0")")
prompt='List the names of every tool you can call, comma-separated, or NONE. Then on a new line, say YES if your instructions contain the word PINEAPPLE, else NO. Nothing else.'
run() {
  name=$1; shift
  before=$(wc -l < "$log" 2>/dev/null || echo 0)
  out=$(cd "$proj" && echo "$prompt" | "$here/clean_env.sh" claude -p --model haiku --output-format json "$@")
  after=$(wc -l < "$log" 2>/dev/null || echo 0)
  echo "== $name | hooks fired: $((after-before))"
  echo "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); u=d["usage"]; print("  tokens in:", u["input_tokens"]+u["cache_read_input_tokens"]+u["cache_creation_input_tokens"], "| ms:", d["duration_ms"]); print("  ", d["result"].replace(chr(10)," / ")[:300])'
}
run baseline
run tools_empty --tools ""
run tools_empty+no_settings --tools "" --setting-sources ""
run safe_mode --tools "" --safe-mode
run full --tools "" --setting-sources "" --strict-mcp-config --no-session-persistence --system-prompt "You are a tutor."
