import io
import json

import pytest
import transcripts as t

from tutor_agent import cli


def test_tui_stub_runs(capsys):
    assert cli.main(["tui"]) == 0
    assert "not implemented" in capsys.readouterr().out


def test_hook_ignores_other_events(monkeypatch, data_dir):
    monkeypatch.delenv("TUTOR_AGENT_INTERNAL", raising=False)
    stdin = io.StringIO('{"hook_event_name": "Notification"}')
    monkeypatch.setattr("sys.stdin", stdin)
    assert cli.main(["hook"]) == 0
    assert stdin.read() == ""


def test_hook_guard_exits_before_reading(monkeypatch):
    monkeypatch.setenv("TUTOR_AGENT_INTERNAL", "1")
    stdin = io.StringIO("payload")
    monkeypatch.setattr("sys.stdin", stdin)
    assert cli.main(["hook"]) == 0
    assert stdin.read() == "payload"


def test_detect_dry_run_logs_batch_and_keeps_offset(tmp_path, data_dir):
    path = t.write(tmp_path / f"{t.SESSION}.jsonl", t.turn(0))
    assert cli.main(["detect", str(path), "--dry-run"]) == 0
    assert cli.main(["detect", str(path), "--dry-run"]) == 0
    log = (data_dir / "tutor.log").read_text()
    assert log.count("dry run") == 2 and '"kind": "edit"' in log


def test_detect_logs_skipped_batch(tmp_path, data_dir):
    path = t.write(tmp_path / f"{t.SESSION}.jsonl", [t.prompt("hi"), t.assistant(t.text("hello"))])
    assert cli.main(["detect", str(path)]) == 0
    assert "skip" in (data_dir / "tutor.log").read_text()


def test_install_uses_claude_config_dir(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["/opt/bin/tutor", "install"])
    assert cli.main(["install", "--yes"]) == 0
    hooks = json.loads((tmp_path / "settings.json").read_text())["hooks"]
    assert set(hooks) == {"Stop", "SubagentStop"}
    assert hooks["Stop"][0]["hooks"][0]["command"] == "/opt/bin/tutor hook"
    assert cli.main(["uninstall", "--yes"]) == 0
    assert json.loads((tmp_path / "settings.json").read_text()) == {}


def test_unknown_command_fails():
    with pytest.raises(SystemExit):
        cli.main(["nope"])
