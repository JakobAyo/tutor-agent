import io
import json
import subprocess
import sys

import pytest
import transcripts as t

from tutor_agent import cli


def test_tui_reports_bad_settings(data_dir, capsys):
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "settings.toml").write_text("nope = 1\n")
    assert cli.main(["tui"]) == 1
    assert "unknown keys" in capsys.readouterr().out


def test_hook_path_never_imports_textual():
    # A fresh interpreter: the TUI tests in this process have imported Textual already (ADR 0009).
    code = ("import sys, io; sys.stdin = io.StringIO('{}'); from tutor_agent import cli; cli.main(['hook']); "
            "assert 'textual' not in sys.modules, 'textual imported'")
    subprocess.run([sys.executable, "-c", code], check=True)


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


def test_detect_skips_subagent_without_transcript(tmp_path, data_dir):
    # Seen in real sessions: SubagentStop for an internal agent whose transcript never exists.
    path = tmp_path / t.SESSION / "subagents" / "agent-a0123456789abcdef.jsonl"
    assert cli.main(["detect", str(path)]) == 0
    log = (data_dir / "tutor.log").read_text()
    assert "no transcript (internal agent)" in log and "Traceback" not in log


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


def _session(name="s1"):
    from tutor_agent import paths
    return t.write(paths.claude_projects_dir() / "-home-u-proj" / f"{name}.jsonl", t.turn(0))


def test_explain_list_makes_no_call(fake_claude, capsys):
    _session()
    assert cli.main(["explain", "--list"]) == 0
    assert "1. proj · just now\n  add caching #0" in capsys.readouterr().out
    assert fake_claude.calls == 0


def test_explain_prints_the_explanation_of_the_most_recent_session(fake_claude, capsys):
    _session()
    assert cli.main(["explain"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("proj · just now") and "echo: PROJECT: /home/u/proj" in out
    assert fake_claude.calls == 1


def test_explain_rejects_a_bad_pick_and_no_sessions(fake_claude, capsys):
    assert cli.main(["explain"]) == 1
    assert "no Claude Code sessions" in capsys.readouterr().err
    _session()
    assert cli.main(["explain", "5"]) == 1
    assert "from 1 to 1" in capsys.readouterr().err
    assert fake_claude.calls == 0
