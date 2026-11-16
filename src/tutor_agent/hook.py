"""The Claude Code hook entry for `Stop` and `SubagentStop` (ADR 0021).

It runs inside every agent turn, so it must be fast and must never fail visibly: it starts
`tutor detect` detached and exits 0, whatever happens. Keep the imports here minimal.
"""

import json
import os
import subprocess
import sys
from typing import Any

INTERNAL_ENV = "TUTOR_AGENT_INTERNAL"  # same value as runner.INTERNAL_ENV, not imported for speed


def detect_args(payload: dict[str, Any]) -> list[str] | None:
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
    from tutor_agent import paths  # noqa: PLC0415  # lazy: keeps the hook's startup minimal

    data = paths.data_dir()
    # stderr goes to the tutor log, so even a crash before logging is set up lands there.
    with paths.log_file().open("a") as err:
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
    except Exception:  # noqa: BLE001  # the hook must never fail visibly in the agent session
        try:
            from tutor_agent.log import get_logger  # noqa: PLC0415  # only needed on failure

            get_logger().exception("hook failed")
        except Exception:  # noqa: BLE001, S110  # nowhere left to report; the agent session must not see it
            pass
    return 0
