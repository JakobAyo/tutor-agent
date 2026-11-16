import os
import time
from typing import Any

import pytest

from tutor_agent import paths, runner
from tutor_agent.runner import ClaudeError

SCHEMA = {"type": "object", "properties": {"echo": {"type": "string"}}, "required": ["echo"]}


def call(fake, **kw):
    kw.setdefault("model", "haiku")
    kw.setdefault("system_prompt", "You are a test.")
    return runner.run("hello", claude_bin=str(fake.bin), **kw)


def flag_value(argv, flag):
    return argv[argv.index(flag) + 1]


def test_uses_sandbox_flag_set(fake_claude):
    call(fake_claude, model="sonnet")
    argv = fake_claude.record["argv"]
    assert argv[0] == "-p"
    assert flag_value(argv, "--model") == "sonnet"
    assert flag_value(argv, "--output-format") == "json"
    assert flag_value(argv, "--tools") == ""
    assert flag_value(argv, "--setting-sources") == ""
    assert "--strict-mcp-config" in argv
    assert "--no-session-persistence" in argv
    assert flag_value(argv, "--system-prompt") == "You are a test."
    assert "--json-schema" not in argv


def test_prompt_goes_to_stdin_not_argv(fake_claude):
    call(fake_claude)
    assert fake_claude.record["stdin"] == "hello"
    assert "hello" not in fake_claude.record["argv"]


def test_runs_from_data_dir(fake_claude, tmp_path, monkeypatch):
    project = tmp_path / "some-project"
    project.mkdir()
    monkeypatch.chdir(project)
    call(fake_claude)
    assert fake_claude.record["cwd"] == str(paths.data_dir())


def test_sets_guard_and_drops_parent_session_env(fake_claude, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "abc")
    call(fake_claude)
    env = fake_claude.record["env"]
    assert env["TUTOR_AGENT_INTERNAL"] == "1"
    assert env["CLAUDECODE"] is None
    assert env["CLAUDE_CODE_SESSION_ID"] is None


def test_returns_text_and_cost(fake_claude):
    result = call(fake_claude)
    assert result.text == "echo: hello"
    assert result.structured is None
    assert result.cost_usd == 0.001


def test_json_schema_returns_structured_output(fake_claude):
    result = call(fake_claude, json_schema=SCHEMA)
    assert result.structured == {"echo": "hello"}
    assert "--json-schema" in fake_claude.record["argv"]


@pytest.mark.parametrize("mode", ["fail", "bad_json", "is_error"])
def test_failures_raise(fake_claude, mode):
    fake_claude.mode(mode)
    with pytest.raises(ClaudeError):
        call(fake_claude)


def test_missing_structured_output_raises(fake_claude):
    fake_claude.mode("no_structured")
    with pytest.raises(ClaudeError, match="structured_output"):
        call(fake_claude, json_schema=SCHEMA)


def ledger() -> list[dict[str, Any]]:
    import json

    return [json.loads(line) for line in paths.usage_file().read_text().splitlines()]


def test_call_is_written_to_the_usage_ledger(fake_claude):
    call(fake_claude, model="sonnet", job="lesson")
    [rec] = ledger()
    assert (rec["job"], rec["model"], rec["cost_usd"], rec["ok"]) == (
        "lesson",
        "sonnet",
        0.001,
        True,
    )
    assert rec["ms"] >= 0 and rec["at"]
    assert paths.usage_file().stat().st_mode & 0o077 == 0


@pytest.mark.parametrize("mode", ["fail", "bad_json", "is_error"])
def test_failed_call_is_in_the_ledger_too(fake_claude, mode):
    fake_claude.mode(mode)
    with pytest.raises(ClaudeError):
        call(fake_claude)
    assert [r["ok"] for r in ledger()] == [False]


def test_unwritable_ledger_does_not_fail_the_call(fake_claude):
    paths.usage_file().mkdir()  # a directory where the file should be
    assert call(fake_claude).text == "echo: hello"
    assert "cannot write usage ledger" in paths.log_file().read_text()


def test_missing_binary_raises(tmp_path):
    with pytest.raises(ClaudeError, match="cannot start"):
        runner.run("x", model="haiku", system_prompt="s", claude_bin=str(tmp_path / "nope"))


def test_timeout_kills_process_group(fake_claude):
    fake_claude.mode("hang")
    start = time.monotonic()
    with pytest.raises(ClaudeError, match="timed out"):
        call(fake_claude, timeout_s=1.5)
    assert time.monotonic() - start < 10
    child_pid = int(
        (fake_claude.record_path.parent / (fake_claude.record_path.name + ".child")).read_text()
    )
    for _ in range(50):
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        pytest.fail("grandchild survived the timeout")


def test_no_env_file_means_no_token(fake_claude, monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    call(fake_claude)
    assert fake_claude.record["env"]["CLAUDE_CODE_OAUTH_TOKEN"] is None


def test_token_from_env_file_is_passed(fake_claude, monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    env_file = paths.env_file()
    env_file.write_text("# comment\nCLAUDE_CODE_OAUTH_TOKEN='sk-ant-oat-secret'\n")
    env_file.chmod(0o600)
    call(fake_claude)
    assert fake_claude.record["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat-secret"  # noqa: S105  # fake token


def test_token_never_reaches_log(fake_claude):
    env_file = paths.env_file()
    env_file.write_text("CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat-leaky\n")
    env_file.chmod(0o600)
    fake_claude.mode("leak_token")
    with pytest.raises(ClaudeError):
        call(fake_claude)
    log = paths.log_file().read_text()
    assert "auth failed for token ***" in log
    assert "sk-ant-oat-leaky" not in log


def test_world_readable_env_file_is_warned(fake_claude):
    env_file = paths.env_file()
    env_file.write_text("CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat-x\n")
    env_file.chmod(0o644)
    call(fake_claude)
    assert "chmod 600" in paths.log_file().read_text()
