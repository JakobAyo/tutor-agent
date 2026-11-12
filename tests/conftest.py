import json
import logging
import sys
from pathlib import Path

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
    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.bin = tmp_path / "claude"
        self.bin.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_CLAUDE}" "$@"\n')
        self.bin.chmod(0o755)
        self.record_path = tmp_path / "fake_claude_record.json"
        self._monkeypatch = monkeypatch
        monkeypatch.setenv("FAKE_CLAUDE_RECORD", str(self.record_path))

    def mode(self, mode: str) -> None:
        self._monkeypatch.setenv("FAKE_CLAUDE_MODE", mode)

    @property
    def record(self) -> dict:
        return json.loads(self.record_path.read_text())


@pytest.fixture
def fake_claude(tmp_path, monkeypatch) -> FakeClaude:
    return FakeClaude(tmp_path, monkeypatch)
