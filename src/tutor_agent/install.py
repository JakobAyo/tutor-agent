"""Add or remove the tutor hook in the global Claude Code settings.

Every change is shown as a diff and needs a yes. The old file is backed up first and the new one
replaces it atomically. Only entries whose command is `<...>tutor hook` are touched.
"""

import copy
import difflib
import json
import os
import re
import shlex
import shutil
import sys
import tempfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

Settings = dict[str, Any]  # parsed ~/.claude/settings.json

HOOK_EVENTS = ("Stop", "SubagentStop")
HOOK_TIMEOUT_S = 10  # Claude Code kills the hook after this; it normally takes ~0.1 s
_OURS = re.compile(r"(^|[/'\"\s])tutor['\"]? hook$")


class InstallError(RuntimeError):
    pass


def settings_path() -> Path:
    base = os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude"
    return Path(base) / "settings.json"


def hook_command() -> str:
    """The absolute path of `tutor`, so the hook doesn't depend on the hook's PATH. Prefers the
    running one (`uv run tutor install` vs the installed tool), else the one on PATH."""
    # Not Path.resolve(): it would follow the ~/.local/bin symlink into uv's tool venv.
    exe = os.path.abspath(sys.argv[0])  # noqa: PTH100
    if Path(exe).name != "tutor":
        found = shutil.which("tutor")
        if not found:
            raise InstallError("no `tutor` command found; run `uv tool install .` first")
        exe = found
    return f"{shlex.quote(exe)} hook"


def is_ours(command: str) -> bool:
    return bool(_OURS.search(command.strip()))


def without_hook(settings: Settings) -> Settings:
    out = copy.deepcopy(settings)
    hooks = out.get("hooks", {})
    for event in HOOK_EVENTS:
        groups = []
        for group in hooks.get(event, []):
            kept = [h for h in group.get("hooks", []) if not is_ours(h.get("command", ""))]
            if kept:
                groups.append({**group, "hooks": kept})
        if groups:
            hooks[event] = groups
        else:
            hooks.pop(event, None)
    if "hooks" in out and not hooks:
        del out["hooks"]
    return out


def with_hook(settings: Settings, command: str) -> Settings:
    """Idempotent: an older tutor entry (e.g. another path) is replaced, never duplicated."""
    hooks = settings.get("hooks", {})
    ours = {
        event: [
            h.get("command")
            for g in hooks.get(event, [])
            for h in g.get("hooks", [])
            if is_ours(h.get("command", ""))
        ]
        for event in HOOK_EVENTS
    }
    if all(cmds == [command] for cmds in ours.values()):
        return copy.deepcopy(settings)  # already installed: don't reorder anything
    out = without_hook(settings)
    hooks = out.setdefault("hooks", {})
    for event in HOOK_EVENTS:
        hooks.setdefault(event, []).append(
            {"hooks": [{"type": "command", "command": command, "timeout": HOOK_TIMEOUT_S}]}
        )
    return out


def apply(
    change: Callable[[Settings], Settings],
    *,
    path: Path | None = None,
    assume_yes: bool = False,
    ask: Callable[[str], str] = input,
    out: Callable[[str], None] = print,
) -> bool:
    """Show the diff of `change` on the settings file, ask, back up, write. True if written."""
    path = path or settings_path()
    old_text = path.read_text(encoding="utf-8") if path.exists() else "{}\n"
    try:
        old = json.loads(old_text)
    except json.JSONDecodeError as e:
        raise InstallError(f"{path} is not valid JSON, not touching it: {e}") from e
    new = change(old)
    if new == old:
        out(f"{path}: nothing to change.")
        return False

    new_text = json.dumps(new, indent=2, ensure_ascii=False) + "\n"
    old_pretty = json.dumps(old, indent=2, ensure_ascii=False) + "\n"
    out(
        "".join(
            difflib.unified_diff(
                old_pretty.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=str(path),
                tofile=str(path) + " (new)",
            )
        )
    )
    if not assume_yes and ask("Write this change? [y/N] ").strip().lower() not in ("y", "yes"):
        out("Nothing written.")
        return False

    if path.exists():
        backup = path.with_name(f"{path.name}.tutor-backup-{datetime.now():%Y%m%d-%H%M%S}")
        backup.write_text(old_text, encoding="utf-8")
        out(f"Backup: {backup}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_text)
        if path.exists():
            Path(tmp).chmod(path.stat().st_mode & 0o777)
        Path(tmp).replace(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    out(f"Wrote {path}.")
    return True


def install(**kwargs: Any) -> bool:
    command = hook_command()
    return apply(lambda s: with_hook(s, command), **kwargs)


def uninstall(**kwargs: Any) -> bool:
    return apply(without_hook, **kwargs)
