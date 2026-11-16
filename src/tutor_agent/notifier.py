"""Desktop notifications through `notify-send`: at most one per detection batch (F4)."""

import subprocess

from tutor_agent.log import get_logger
from tutor_agent.store import Concept

APP_NAME = "Tutor"
TIMEOUT_S = 5  # notify-send returns at once; a hung D-Bus must not keep the detector alive


def message(concepts: list[Concept]) -> tuple[str, str]:
    """(title, body) for the new concepts."""
    title = f"{len(concepts)} new concept{'s' if len(concepts) > 1 else ''} to learn"
    body = "\n".join(f"• {c.name} ({c.category})" for c in concepts)
    return title, body


def notify(concepts: list[Concept], *, muted: bool, notify_bin: str = "notify-send") -> bool:
    """Send one notification naming `concepts`. True if one was sent. Never raises."""
    log = get_logger()
    if not concepts:
        return False
    if muted:
        log.info("muted, no notification for %s", [c.name for c in concepts])
        return False
    title, body = message(concepts)
    try:
        subprocess.run(
            [notify_bin, f"--app-name={APP_NAME}", "--", title, body],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=TIMEOUT_S,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("notification failed (%s): %s", notify_bin, e)
        return False
    return True
