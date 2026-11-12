"""Spike Q1/Q4: hook that appends its stdin payload plus selected env vars to a log.

Usage (as a Claude Code hook command): python3 /abs/path/dump_hook.py /abs/log.jsonl
"""
import json, os, sys, time
t0 = time.perf_counter()
payload = json.load(sys.stdin)
env = {k: os.environ.get(k) for k in ("TUTOR_AGENT_INTERNAL", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_PROJECT_DIR")}
with open(sys.argv[1], "a") as f:
    f.write(json.dumps({"payload": payload, "env": env, "ts": time.time()}) + "\n")
