import json
from typing import Any

import pytest

from tutor_agent import install

CMD = "/home/u/.local/bin/tutor hook"


def our_commands(settings):
    return [
        h["command"]
        for event in install.HOOK_EVENTS
        for g in settings.get("hooks", {}).get(event, [])
        for h in g["hooks"]
        if install.is_ours(h["command"])
    ]


@pytest.mark.parametrize(
    ("command", "ours"),
    [
        (CMD, True),
        ("tutor hook", True),
        ("'/path with space/tutor' hook", True),
        ("/usr/bin/other-tutor hook", False),
        ("tutor hooks", False),
        ("echo tutor hook && rm x", False),
    ],
)
def test_is_ours(command, ours):
    assert install.is_ours(command) is ours


def test_with_hook_keeps_other_hooks_and_is_idempotent():
    theirs = {"hooks": [{"type": "command", "command": "notify.sh"}]}
    settings: dict[str, Any] = {
        "model": "opus",
        "hooks": {"Stop": [theirs], "PreToolUse": [theirs]},
    }
    once = install.with_hook(settings, CMD)
    assert once["model"] == "opus" and once["hooks"]["PreToolUse"] == [theirs]
    assert once["hooks"]["Stop"][0] == theirs
    assert our_commands(once) == [CMD, CMD]
    assert install.with_hook(once, CMD) == once
    assert settings["hooks"]["Stop"] == [theirs]  # input not mutated


def test_reinstall_with_new_path_replaces_old_entry():
    old = install.with_hook({}, "/old/tutor hook")
    assert our_commands(install.with_hook(old, CMD)) == [CMD, CMD]


def test_without_hook_restores_original():
    theirs = {"hooks": [{"type": "command", "command": "notify.sh"}]}
    original = {"hooks": {"Stop": [theirs]}}
    assert install.without_hook(install.with_hook(original, CMD)) == original
    assert install.without_hook(install.with_hook({}, CMD)) == {}


def test_without_hook_keeps_mixed_group():
    group = {
        "hooks": [{"type": "command", "command": "notify.sh"}, {"type": "command", "command": CMD}]
    }
    out = install.without_hook({"hooks": {"Stop": [group]}})
    assert out == {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "notify.sh"}]}]}}


def test_apply_asks_backs_up_and_writes(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"model": "opus"}\n')
    path.chmod(0o600)
    lines: list[str] = []
    assert install.apply(
        lambda s: install.with_hook(s, CMD), path=path, ask=lambda _: "y", out=lines.append
    )
    assert our_commands(json.loads(path.read_text())) == [CMD, CMD]
    assert path.stat().st_mode & 0o777 == 0o600
    (backup,) = tmp_path.glob("settings.json.tutor-backup-*")
    assert backup.read_text() == '{"model": "opus"}\n'
    assert CMD in lines[0]  # the diff was shown


def test_apply_declined_writes_nothing(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{}\n")
    assert not install.apply(
        lambda s: install.with_hook(s, CMD), path=path, ask=lambda _: "", out=lambda _: None
    )
    assert path.read_text() == "{}\n" and list(tmp_path.iterdir()) == [path]


def test_apply_refuses_invalid_json(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{oops")
    with pytest.raises(install.InstallError):
        install.apply(install.without_hook, path=path, assume_yes=True, out=lambda _: None)


def test_apply_creates_missing_file_without_backup(tmp_path):
    path = tmp_path / "claude/settings.json"
    install.apply(
        lambda s: install.with_hook(s, CMD), path=path, assume_yes=True, out=lambda _: None
    )
    assert our_commands(json.loads(path.read_text())) == [CMD, CMD]
    assert list(path.parent.iterdir()) == [path]


def test_hook_command_falls_back_to_path(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/x/cli.py"])
    monkeypatch.setattr("shutil.which", lambda name: "/home/u/.local/bin/tutor")
    assert install.hook_command() == CMD
    monkeypatch.setattr("shutil.which", lambda name: None)
    with pytest.raises(install.InstallError):
        install.hook_command()


def test_settings_path_honours_claude_config_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    assert install.settings_path() == tmp_path / "settings.json"
