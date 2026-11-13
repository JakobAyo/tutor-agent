"""Where the tutor keeps its files. Everything lives in one data directory."""

import os
from pathlib import Path

DATA_DIR_ENV = "TUTOR_AGENT_DATA_DIR"


def data_dir() -> Path:
    """The data directory, created on first use. `TUTOR_AGENT_DATA_DIR` overrides it (tests)."""
    override = os.environ.get(DATA_DIR_ENV)
    base = Path(override) if override else Path.home() / ".local/share/tutor-agent"
    base.mkdir(parents=True, exist_ok=True)
    return base


def concepts_file() -> Path:
    return data_dir() / "concepts.json"


def settings_file() -> Path:
    return data_dir() / "settings.toml"


def env_file() -> Path:
    return data_dir() / ".env"


def lessons_dir() -> Path:
    return data_dir() / "lessons"


def usage_file() -> Path:
    return data_dir() / "usage.jsonl"


def log_file() -> Path:
    return data_dir() / "tutor.log"


def claude_projects_dir() -> Path:
    """Where Claude Code keeps session transcripts. Honours `CLAUDE_CONFIG_DIR`, like Claude Code."""
    base = os.environ.get("CLAUDE_CONFIG_DIR")
    return (Path(base) if base else Path.home() / ".claude") / "projects"
