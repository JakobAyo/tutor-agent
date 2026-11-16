"""Read only the new part of a transcript and turn it into a batch of events.

Offsets live in `offsets/<session_id>.json`, one entry per transcript of the session (main and
subagents). Reading and saving the offset happen under a per-session `flock`, so two hooks that
fire close together (e.g. `Stop` twice while a background subagent finishes) never read the same
lines twice. The lock is released before detection, which is slow.
"""

import fcntl
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from tutor_agent import paths
from tutor_agent.events import Event, EventMapper
from tutor_agent.log import get_logger

# A batch larger than this is almost always a backlog (tutor installed mid-session, resumed
# session), not one turn. Keep the newest events; the detector only needs the recent work.
MAX_EVENTS = 150
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass
class Batch:
    transcript: Path
    session_id: str
    first_line: int  # 1-based, inclusive
    last_line: int  # 1-based, inclusive; first_line - 1 when nothing new
    events: list[Event] = field(default_factory=list)
    skipped_lines: int = 0  # complete lines that were not valid JSON
    dropped_events: int = 0  # cut by MAX_EVENTS


def session_id_for(transcript: Path) -> str:
    """`<sid>.jsonl` for the main agent, `<sid>/subagents/agent-<id>.jsonl` for a subagent."""
    if transcript.parent.name == "subagents":
        return transcript.parent.parent.name
    return transcript.stem


def read_new(transcript: Path, session_id: str | None = None, *, advance: bool = True) -> Batch:
    """All events after the saved offset. With `advance=False` the offset stays (dry runs)."""
    transcript = transcript.resolve()
    session_id = session_id or session_id_for(transcript)
    if not _SAFE_ID.match(session_id):
        raise ValueError(f"unsafe session id: {session_id!r}")

    directory = paths.data_dir() / "offsets"
    directory.mkdir(exist_ok=True)
    offsets_path = directory / f"{session_id}.json"
    with open(directory / f"{session_id}.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            offsets = _load(offsets_path)
            pos = offsets.get(str(transcript), {"byte": 0, "line": 0})
            batch, new_pos = _read_from(transcript, session_id, pos)
            if advance and new_pos != pos:
                offsets[str(transcript)] = new_pos
                _save(offsets_path, offsets)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
    return batch


def _read_from(transcript: Path, session_id: str, pos: dict) -> tuple[Batch, dict]:
    log = get_logger()
    byte, line = pos["byte"], pos["line"]
    if transcript.stat().st_size < byte:
        log.warning("%s shrank below its offset, reading it from the start", transcript)
        byte, line = 0, 0

    mapper = EventMapper()
    events: list[Event] = []
    skipped = 0
    first_line = line + 1
    with open(transcript, "rb") as f:
        f.seek(byte)
        for raw in f:
            if not raw.endswith(b"\n"):
                break  # partly written last line: leave it for the next read
            byte += len(raw)
            line += 1
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                skipped += 1  # complete but broken: skip it, or we would stop here forever
                continue
            if isinstance(rec, dict):
                events.extend(mapper.map(rec, f"{transcript}:{line}"))

    dropped = max(0, len(events) - MAX_EVENTS)
    if skipped:
        log.warning("%s: skipped %d invalid JSON lines", transcript, skipped)
    if dropped:
        log.info(
            "%s: batch too large, kept the newest %d of %d events",
            transcript,
            MAX_EVENTS,
            len(events),
        )
    batch = Batch(transcript, session_id, first_line, line, events[dropped:], skipped, dropped)
    return batch, {"byte": byte, "line": line}


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        # Losing offsets only means one batch is re-read; refusing would stop all detection.
        get_logger().warning("%s is corrupt, starting the session's offsets over", path)
        return {}


def _save(path: Path, offsets: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(offsets, f, indent=1)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
