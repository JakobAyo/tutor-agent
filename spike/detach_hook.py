"""Spike Q4/Q5/Q6: minimal hook entry that starts a detached worker and exits.

Usage (hook command): python3 detach_hook.py <log>
Logs hook wall time. Exits at once if TUTOR_AGENT_INTERNAL is set (recursion guard).
"""
import json, os, subprocess, sys, time
t0 = time.perf_counter()
log = sys.argv[1]
if os.environ.get("TUTOR_AGENT_INTERNAL"):
    with open(log, "a") as f:
        f.write(json.dumps({"guard": "skipped"}) + "\n")
    sys.exit(0)
payload = sys.stdin.read()
subprocess.Popen(
    [sys.executable, os.path.join(os.path.dirname(__file__), "detached_worker.py"), log],
    stdin=subprocess.PIPE if False else subprocess.DEVNULL,
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    start_new_session=True,  # own process group: survives the hook and the session
    env={**os.environ, "TUTOR_PAYLOAD": payload},
)
with open(log, "a") as f:
    f.write(json.dumps({"hook_ms": round((time.perf_counter() - t0) * 1000, 1)}) + "\n")
