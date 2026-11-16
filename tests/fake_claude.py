"""Stand-in for the `claude` binary in runner tests. Never calls a model.

It writes what it received (argv, cwd, stdin, selected env vars) to `$FAKE_CLAUDE_RECORD` and
behaves according to `$FAKE_CLAUDE_MODE`. `$FAKE_CLAUDE_STRUCTURED` (JSON) is returned as
`structured_output`. Every call appends a line to `$FAKE_CLAUDE_RECORD.calls`.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

WATCHED_ENV = (
    "TUTOR_AGENT_INTERNAL",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDECODE",
    "CLAUDE_CODE_SESSION_ID",
)


def main() -> int:
    args = sys.argv[1:]
    prompt = sys.stdin.read()
    mode = os.environ.get("FAKE_CLAUDE_MODE", "ok")
    record = Path(os.environ["FAKE_CLAUDE_RECORD"])
    with record.open("w") as f:
        json.dump(
            {
                "argv": args,
                "cwd": str(Path.cwd()),
                "stdin": prompt,
                "env": {k: os.environ.get(k) for k in WATCHED_ENV},
            },
            f,
        )
    with Path(f"{record}.calls").open("a") as f:
        f.write(mode + "\n")

    if mode == "fail":
        print("boom", file=sys.stderr)
        return 1
    if mode == "leak_token":
        print(f"auth failed for token {os.environ.get('CLAUDE_CODE_OAUTH_TOKEN')}", file=sys.stderr)
        return 1
    if mode == "bad_json":
        print("this is not json")
        return 0
    if mode == "hang":
        # A grandchild too, to check the whole process group is killed on timeout.
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        with Path(f"{record}.child").open("w") as f:
            f.write(str(child.pid))
        time.sleep(60)
        return 0

    out = {
        "type": "result",
        "subtype": "success",
        "is_error": mode == "is_error",
        "result": f"echo: {prompt}",
        "total_cost_usd": 0.001,
    }
    if "--json-schema" in args and mode != "no_structured":
        canned = os.environ.get("FAKE_CLAUDE_STRUCTURED")
        out["structured_output"] = json.loads(canned) if canned else {"echo": prompt}
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
