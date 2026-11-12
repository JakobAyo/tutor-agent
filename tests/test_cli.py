import io

import pytest

from tutor_agent import cli


@pytest.mark.parametrize("command", ["detect", "tui"])
def test_stubs_run(command, capsys):
    assert cli.main([command]) == 0
    assert "not implemented" in capsys.readouterr().out


def test_hook_consumes_stdin_and_exits_zero(monkeypatch):
    monkeypatch.delenv("TUTOR_AGENT_INTERNAL", raising=False)
    stdin = io.StringIO('{"hook_event_name": "Stop"}')
    monkeypatch.setattr("sys.stdin", stdin)
    assert cli.main(["hook"]) == 0
    assert stdin.read() == ""


def test_hook_guard_exits_before_reading(monkeypatch):
    monkeypatch.setenv("TUTOR_AGENT_INTERNAL", "1")
    stdin = io.StringIO("payload")
    monkeypatch.setattr("sys.stdin", stdin)
    assert cli.main(["hook"]) == 0
    assert stdin.read() == "payload"


def test_unknown_command_fails():
    with pytest.raises(SystemExit):
        cli.main(["nope"])
