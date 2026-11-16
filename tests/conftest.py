import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from tutor_agent.log import LOGGER_NAME, TutorFileHandler

FAKE_CLAUDE = Path(__file__).with_name("fake_claude.py")


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    """Every test gets its own data directory and a fresh log handler pointing into it."""
    d = tmp_path / "data"
    monkeypatch.setenv("TUTOR_AGENT_DATA_DIR", str(d))
    _drop_tutor_handlers()
    yield d
    _drop_tutor_handlers()


def _drop_tutor_handlers() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    for h in list(logger.handlers):
        if isinstance(h, TutorFileHandler):
            logger.removeHandler(h)
            h.close()


class FakeClaude:
    def __init__(self, bin_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.bin = bin_dir / "claude"
        self.bin.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_CLAUDE}" "$@"\n')
        self.bin.chmod(0o755)
        self.record_path = bin_dir / "fake_claude_record.json"
        self.calls_path = bin_dir / "fake_claude_record.json.calls"
        self._monkeypatch = monkeypatch
        monkeypatch.setenv("FAKE_CLAUDE_RECORD", str(self.record_path))
        monkeypatch.delenv("FAKE_CLAUDE_MODE", raising=False)
        monkeypatch.delenv("FAKE_CLAUDE_STRUCTURED", raising=False)

    def mode(self, mode: str) -> None:
        self._monkeypatch.setenv("FAKE_CLAUDE_MODE", mode)

    def answer(self, structured) -> None:
        """Make the fake return this `structured_output` for `--json-schema` calls."""
        self._monkeypatch.setenv("FAKE_CLAUDE_STRUCTURED", json.dumps(structured))

    @property
    def record(self) -> dict[str, Any]:
        data: dict[str, Any] = json.loads(self.record_path.read_text())
        return data

    @property
    def calls(self) -> int:
        return len(self.calls_path.read_text().splitlines()) if self.calls_path.exists() else 0


class FakeNotifySend:
    """Records each `notify-send` call as one JSON line (its argv)."""

    def __init__(self, bin_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.record_path = bin_dir / "notify-send.jsonl"
        script = bin_dir / "notify-send"
        script.write_text(
            f"#!{sys.executable}\nimport json, sys\n"
            f'open({str(self.record_path)!r}, "a").write(json.dumps(sys.argv[1:]) + "\\n")\n'
        )
        script.chmod(0o755)

    @property
    def calls(self) -> list[list[str]]:
        if not self.record_path.exists():
            return []
        return [json.loads(line) for line in self.record_path.read_text().splitlines()]


@pytest.fixture(autouse=True)
def fake_bins(request, tmp_path_factory, monkeypatch):
    """Offline tests get a fake `claude` and `notify-send` first on PATH, also for subprocesses
    such as the detached detector, so no test spends usage or shows a notification."""
    if request.node.get_closest_marker("real") or request.node.get_closest_marker("prompt"):
        yield None
        return
    bin_dir = tmp_path_factory.mktemp("bin")  # not in tmp_path: some tests check what is there
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    # Never read my real sessions. Not for real calls: `claude` keeps its login there.
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path_factory.mktemp("claude-home")))
    yield FakeClaude(bin_dir, monkeypatch), FakeNotifySend(bin_dir, monkeypatch)


@pytest.fixture
def fake_claude(fake_bins) -> FakeClaude:
    claude: FakeClaude = fake_bins[0]
    return claude


@pytest.fixture
def fake_notify(fake_bins) -> FakeNotifySend:
    notify: FakeNotifySend = fake_bins[1]
    return notify
