"""What `tutor detect` does with one transcript: read the new batch, pre-filter, detect.

Runs detached from the hook, so every failure is logged here and nowhere else.
"""

from pathlib import Path

from tutor_agent import events, prefilter, reader
from tutor_agent.log import get_logger


def process(transcript: Path, session_id: str | None, *, dry_run: bool) -> int:
    log = get_logger()
    try:
        batch = reader.read_new(transcript, session_id, advance=not dry_run)
        where = f"{batch.transcript.name} lines {batch.first_line}-{batch.last_line}"
        reason = prefilter.skip_reason(batch.events)
        if reason:
            log.info("skip %s: %s", where, reason)
            return 0
        if dry_run:
            log.info("dry run %s, %d events:\n%s", where, len(batch.events), events.to_json(batch.events))
            return 0
        # M3: detection call, storing, notification.
        log.info("batch %s: %d events (detection not implemented yet)", where, len(batch.events))
        return 0
    except Exception:
        log.exception("detect failed for %s", transcript)
        return 1
