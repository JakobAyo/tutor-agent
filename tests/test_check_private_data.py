"""Tests for scripts/check_private_data.py.

Real-looking values are built by concatenation so this file doesn't trip the check itself.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).parent.parent / "scripts" / "check_private_data.py"
_spec = importlib.util.spec_from_file_location("check_private_data", _SCRIPT)
assert _spec is not None
assert _spec.loader is not None
cpd = importlib.util.module_from_spec(_spec)
sys.modules["check_private_data"] = cpd
_spec.loader.exec_module(cpd)

NAME = "jo" + "hndoe"


def kinds(line: str, terms: list[str] | None = None) -> list[str]:
    return [f.kind for f in cpd.check_line("f.py", 1, line, terms or [])]


@pytest.mark.parametrize(
    "line",
    [
        "path = '/home/u/.claude/projects'",
        "cwd: /home/me/project",
        "/Users/user/code",
        "~/.claude/projects/-home-u-proj/abc.jsonl",
        "-home-user-tutor-agent",
        "Co-Authored-By: Claude <noreply@anthropic.com>",
        "JakobAyo@users.noreply.github.com",
        "mail someone@example.com",
        "@pytest.mark.parametrize('a@b.co', [1])",
        "/home/runner/work/x",
    ],
)
def test_placeholders_and_allowed_values_pass(line: str) -> None:
    assert kinds(line) == []


@pytest.mark.parametrize(
    ("line", "kind"),
    [
        (f"/home/{NAME}/Projects/x", "home-path"),
        (f"/Users/{NAME}/x", "home-path"),
        (f"C:\\Users\\{NAME}\\x", "home-path"),
        (f"projects/-home-{NAME}-Projects-x/1.jsonl", "project-slug"),
        (f"{NAME}@" + "corp-mail.de", "email"),
    ],
)
def test_real_looking_values_are_found(line: str, kind: str) -> None:
    assert kind in kinds(line)


def test_findings_are_redacted() -> None:
    (finding,) = cpd.check_line("f.py", 3, f"x /home/{NAME}/y", [])
    assert NAME not in str(finding)
    assert str(finding).startswith("f.py:3:3: home-path: /home/" + NAME[0])


def test_private_terms_match_whole_words_case_insensitively() -> None:
    terms = ["Acme Corp"]
    assert kinds("works at ACME corp.", terms) == ["private-term"]
    assert kinds("acmecorporation", terms) == []
    (finding,) = cpd.check_line("f.py", 1, "acme corp", terms)
    assert "acme" not in str(finding).lower()


def test_allow_marker_skips_the_line() -> None:
    assert kinds(f"/home/{NAME}/x  # private-data: allow") == []


def test_terms_come_from_env_and_file(tmp_path: Path) -> None:
    terms_file = tmp_path / ".private-terms"
    terms_file.write_text("# comment\nFoo Bar\n\n", encoding="utf-8")
    assert cpd.load_terms("baz, qux\n", terms_file) == ["Foo Bar", "baz", "qux"]
    assert cpd.load_terms(None, tmp_path / "missing") == []


def test_main_reports_and_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    clean = tmp_path / "clean.json"
    clean.write_text('{"cwd": "/home/u/x"}\n', encoding="utf-8")
    leaky = tmp_path / "leaky.json"
    leaky.write_text(f'{{"cwd": "/home/{NAME}/x"}}\n', encoding="utf-8")
    binary = tmp_path / "blob.bin"
    binary.write_bytes(b"\xff\xfe/home/" + NAME.encode())

    assert cpd.main([str(clean), str(binary)]) == 0
    assert cpd.main([str(clean), str(leaky)]) == 1
    out = capsys.readouterr()
    assert "leaky.json:1:10: home-path" in out.out
    assert NAME not in out.out + out.err


def test_repository_is_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real gate: every tracked file passes (CI also runs the script directly)."""
    monkeypatch.chdir(_SCRIPT.parent.parent)
    monkeypatch.delenv("PRIVATE_TERMS", raising=False)
    assert cpd.main([]) == 0
