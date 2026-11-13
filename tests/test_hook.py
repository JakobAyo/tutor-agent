import io
import json
import os
import subprocess
import sys
import time

import pytest
import transcripts as t

from tutor_agent import hook


def stop(path, **extra):
    return {"hook_event_name": "Stop", "session_id": t.SESSION, "transcript_path": str(path), **extra}


def test_stop_reads_main_transcript():
    assert hook.detect_args(stop("/m.jsonl")) == ["detect", "/m.jsonl", "--session-id", t.SESSION]


def test_subagent_stop_reads_agent_transcript():
    payload = stop("/m.jsonl", hook_event_name="SubagentStop", agent_transcript_path="/s.jsonl")
    assert hook.detect_args(payload)[1] == "/s.jsonl"


def test_other_events_are_ignored():
    assert hook.detect_args({"hook_event_name": "PreToolUse"}) is None


def test_missing_path_is_an_error():
    with pytest.raises(ValueError):
        hook.detect_args({"hook_event_name": "SubagentStop", "session_id": "s"})


@pytest.mark.parametrize("stdin", ["not json", '{"hook_event_name": "Stop"}'])
def test_bad_payload_is_logged_not_raised(stdin, monkeypatch, data_dir, capsys):
    monkeypatch.delenv("TUTOR_AGENT_INTERNAL", raising=False)
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    assert hook.main() == 0
    assert capsys.readouterr() == ("", "")
    assert "hook failed" in (data_dir / "tutor.log").read_text()


def run_hook(payload: dict, env: dict | None = None) -> tuple[subprocess.CompletedProcess, float]:
    start = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "tutor_agent.cli", "hook"],
        input=json.dumps(payload), capture_output=True, text=True, env={**os.environ, **(env or {})},
    )
    return proc, time.perf_counter() - start


def wait_for(predicate, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_hook_starts_detached_detect(tmp_path, data_dir):
    """End to end: the hook returns at once, silent, and the detector runs (on the fake claude)."""
    path = t.write(tmp_path / f"{t.SESSION}.jsonl", t.turn(0))
    proc, _ = run_hook(stop(path))
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")
    log = data_dir / "tutor.log"
    assert wait_for(lambda: log.exists() and "detected" in log.read_text())
    assert (data_dir / "offsets" / f"{t.SESSION}.json").exists()


def test_detect_crash_lands_only_in_the_log(tmp_path, data_dir):
    proc, _ = run_hook(stop(tmp_path / "missing.jsonl"))
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")
    log = data_dir / "tutor.log"
    assert wait_for(lambda: log.exists() and "detect failed" in log.read_text())
    assert "FileNotFoundError" in log.read_text()


def test_guard_stops_the_hook(tmp_path, data_dir):
    path = t.write(tmp_path / f"{t.SESSION}.jsonl", t.turn(0))
    proc, _ = run_hook(stop(path), {"TUTOR_AGENT_INTERNAL": "1"})
    assert proc.returncode == 0
    time.sleep(0.5)
    assert not (data_dir / "offsets").exists()
