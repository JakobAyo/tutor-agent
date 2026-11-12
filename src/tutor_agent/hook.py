"""The Claude Code hook entry for `Stop` and `SubagentStop` (ADR 0021).

It runs inside every agent turn, so it must be fast and must never fail visibly: it starts
`tutor detect` detached and exits 0, whatever happens. Keep the imports here minimal.
"""

import json
import os
import subprocess
import sys

INTERNAL_ENV = "TUTOR_AGENT_INTERNAL"  # same value as runner.INTERNAL_ENV, not imported for speed


def detect_args(payload: dict) -> list[str] | None:
    """The `tutor detect` arguments for this hook event, or None if the event isn't ours."""
    event = payload.get("hook_event_name")
    if event == "Stop":
        transcript = payload.get("transcript_path")
    elif event == "SubagentStop":
        transcript = payload.get("agent_transcript_path")
    else:
        return None
    session_id = payload.get("session_id")
    if not transcript or not session_id:
        raise ValueError(f"{event} payload without transcript path or session id")
    return ["detect", transcript, "--session-id", session_id]


def spawn_detect(args: list[str]) -> None:
    from tutor_agent import paths  # light: os and pathlib only

    data = paths.data_dir()
    # stderr goes to the tutor log, so even a crash before logging is set up lands there.
    with open(paths.log_file(), "a") as err:
        subprocess.Popen(
            [sys.executable, "-m", "tutor_agent.cli", *args],
            cwd=data,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=err,
            start_new_session=True,  # own session: survives the hook and the agent session
        )


def main() -> int:
    # Recursion guard, layer 2 (ADR 0022). Must stay the first thing the hook does.
    if os.environ.get(INTERNAL_ENV) == "1":
        return 0
    try:
        args = detect_args(json.loads(sys.stdin.read()))
        if args:
            spawn_detect(args)
    except Exception:
        try:
            from tutor_agent.log import get_logger

            get_logger().exception("hook failed")
        except Exception:
            pass  # nowhere left to report; the agent session must not see it
    return 0
