"""The only place that calls `claude -p` (ADR 0011, 0022).

Every call: no tools, no MCP servers, no settings (so no hooks), no saved session, the tutor's own
system prompt, run from the data directory. `TUTOR_AGENT_INTERNAL=1` is a second recursion guard.
"""

import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tutor_agent import paths
from tutor_agent.log import get_logger, register_secret

INTERNAL_ENV = "TUTOR_AGENT_INTERNAL"
TOKEN_ENV = "CLAUDE_CODE_OAUTH_TOKEN"

# Set by the Claude Code session that started the hook. Dropping them makes the call behave like
# a fresh top-level `claude -p` instead of a nested child of the observed session.
PARENT_SESSION_ENV = (
    "CLAUDECODE",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_PID",
    "CLAUDE_CODE_MESSAGING_SOCKET",
    "CLAUDE_CODE_MESSAGING_TOKEN",
    "CLAUDE_CODE_SESSION_ATTENDED",
    "AI_AGENT",
    "CLAUDE_CODE_EXECPATH",
    "CLAUDE_EFFORT",
)


class ClaudeError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunResult:
    text: str
    structured: Any
    duration_ms: int
    cost_usd: float | None
    raw: dict


def build_command(claude_bin: str, model: str, system_prompt: str, json_schema: dict | None) -> list[str]:
    cmd = [
        claude_bin, "-p",
        "--model", model,
        "--output-format", "json",
        "--tools", "",
        "--setting-sources", "",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--system-prompt", system_prompt,
    ]
    if json_schema is not None:
        cmd += ["--json-schema", json.dumps(json_schema)]
    return cmd


def load_token(env_path: Path | None = None) -> str | None:
    """The optional `claude setup-token` token from the data directory's `.env` (ADR 0019)."""
    env_path = env_path or paths.env_file()
    if not env_path.exists():
        return None
    if env_path.stat().st_mode & 0o077:
        get_logger().warning("%s is readable by other users; run: chmod 600 %s", env_path, env_path)
    for line in env_path.read_text().splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key.strip() == TOKEN_ENV:
            token = value.strip().strip("'\"")
            register_secret(token)
            return token or None
    return None


def build_env(token: str | None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in PARENT_SESSION_ENV}
    env[INTERNAL_ENV] = "1"
    if token:
        env[TOKEN_ENV] = token
    return env


def run(
    prompt: str,
    *,
    model: str,
    system_prompt: str,
    json_schema: dict | None = None,
    timeout_s: float = 120.0,
    claude_bin: str = "claude",
) -> RunResult:
    """Run one sandboxed call. The prompt goes in on stdin, because `--tools ""` would swallow
    a positional prompt. Raises `ClaudeError` on any failure; never returns a half result."""
    log = get_logger()
    cwd = paths.data_dir()
    cmd = build_command(claude_bin, model, system_prompt, json_schema)
    env = build_env(load_token())

    start = time.monotonic()
    try:
        # Own process group, so a timeout kills claude and anything it started.
        proc = subprocess.Popen(
            cmd, cwd=cwd, env=env, text=True, start_new_session=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except OSError as e:
        raise ClaudeError(f"cannot start {claude_bin!r}: {e}") from e
    try:
        stdout, stderr = proc.communicate(prompt, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        log.error("claude timed out after %ss (model=%s)", timeout_s, model)
        raise ClaudeError(f"claude timed out after {timeout_s}s") from None
    duration_ms = round((time.monotonic() - start) * 1000)

    if proc.returncode != 0:
        log.error("claude exited %s (model=%s): %s", proc.returncode, model, (stderr or stdout)[-500:])
        raise ClaudeError(f"claude exited with code {proc.returncode}")
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        log.error("claude returned non-JSON output (model=%s): %s", model, stdout[-500:])
        raise ClaudeError("claude returned non-JSON output") from None
    if data.get("is_error"):
        log.error("claude reported an error (model=%s): %s", model, str(data.get("result"))[-500:])
        raise ClaudeError(f"claude reported an error: {data.get('subtype', 'unknown')}")

    structured = data.get("structured_output")
    if json_schema is not None and structured is None:
        log.error("claude returned no structured_output (model=%s)", model)
        raise ClaudeError("claude returned no structured_output")

    log.info("claude ok model=%s ms=%s cost_usd=%s", model, duration_ms, data.get("total_cost_usd"))
    return RunResult(
        text=data.get("result", ""),
        structured=structured,
        duration_ms=duration_ms,
        cost_usd=data.get("total_cost_usd"),
        raw=data,
    )
