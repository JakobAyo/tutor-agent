"""Spike Q5/Q8: detached worker that runs one sandboxed `claude -p` call and logs the outcome."""
import json, os, subprocess, sys, time
log = sys.argv[1]
time.sleep(3)  # make sure the parent session has already exited
data_dir = os.path.expanduser("~/.local/share/tutor-agent-spike")
os.makedirs(data_dir, exist_ok=True)
t0 = time.perf_counter()
p = subprocess.run(
    ["claude", "-p", "--model", "haiku", "--output-format", "json", "--tools", "",
     "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence",
     "--system-prompt", "Reply with one word."],
    input="Say OK.", capture_output=True, text=True, cwd=data_dir,
    env={**os.environ, "TUTOR_AGENT_INTERNAL": "1"},
)
out = {"worker_rc": p.returncode, "ms": round((time.perf_counter() - t0) * 1000),
       "parent_alive": os.getppid() != 1, "stderr": p.stderr[-300:]}
try:
    out["result"] = json.loads(p.stdout)["result"]
except Exception:
    out["stdout"] = p.stdout[-300:]
with open(log, "a") as f:
    f.write(json.dumps(out) + "\n")
