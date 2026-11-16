"""User settings from `settings.toml` in the data directory. Every key is optional."""

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

from tutor_agent import paths


@dataclass(frozen=True)
class Settings:
    detect_model: str = "haiku"
    lesson_model: str = "sonnet"
    muted: bool = False
    claude_bin: str = "claude"
    claude_timeout_s: float = 120.0


class SettingsError(ValueError):
    pass


def load(path: Path | None = None) -> Settings:
    path = path or paths.settings_file()
    if not path.exists():
        return Settings()
    try:
        raw = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        raise SettingsError(f"{path}: {e}") from e

    known = {f.name: f for f in fields(Settings)}
    unknown = set(raw) - set(known)
    if unknown:
        raise SettingsError(f"{path}: unknown keys {sorted(unknown)}")
    for key, value in raw.items():
        expected = known[key].type
        ok = (
            isinstance(value, (int, float)) and not isinstance(value, bool)
            if expected is float
            else isinstance(value, expected)
        )
        if not ok:
            raise SettingsError(f"{path}: '{key}' must be {expected.__name__}, got {value!r}")
    return Settings(**raw)
