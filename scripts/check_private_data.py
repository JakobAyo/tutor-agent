"""Fail if tracked files contain private data that a transcript-reading tool tends to leak.

tutor-agent works on real Claude Code transcripts, so test fixtures, spike results and docs
can easily pick up a home directory, a Claude project slug, an email address, or a name.
Generic secret scanners (gitleaks, GitHub secret scanning) don't look for these.

Usage:
    check_private_data.py [FILE ...]    # no files: check every tracked file (git ls-files)

Checks:
    home-path       /home/<name>, /Users/<name>, C:\\Users\\<name> with a real-looking name
    project-slug    Claude Code project dirs like -home-<name>-...
    email           any address outside the allowed noreply/example domains
    private-term    terms from $PRIVATE_TERMS and the untracked file .private-terms
                    (one per line, case-insensitive; e.g. your name, employer, internal projects)

A line containing "private-data: allow" is skipped. Findings are printed redacted, because
CI logs of a public repo are public too.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ALLOW_MARKER = "private-data: allow"
TERMS_FILE = ".private-terms"

# Placeholder user names that tests and docs use on purpose.
PLACEHOLDER_USERS = frozenset(
    {"u", "me", "user", "you", "runner", "example", "someone", "name", "username", "alice", "bob"}
)
ALLOWED_EMAILS = frozenset({"noreply@anthropic.com", "noreply@github.com"})
ALLOWED_EMAIL_DOMAINS = ("users.noreply.github.com", "example.com", "example.org", "example.net")

_USER = r"([A-Za-z0-9][A-Za-z0-9._-]*)"
HOME_PATH = re.compile(r"(?:/home/|/Users/|[A-Za-z]:\\\\?Users\\\\?)" + _USER)
PROJECT_SLUG = re.compile(r"-(?:home|Users)-" + r"([A-Za-z0-9][A-Za-z0-9_]*)-")
EMAIL = re.compile(
    r"(?<![\w.@])[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})"
)
# Python decorators and the like look like emails to the regex above.
_NOT_AN_EMAIL = re.compile(r"@(?:pytest|dataclass|property|staticmethod|classmethod)\b")

SKIP_SUFFIXES = (".lock", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".whl", ".gz")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    column: int
    kind: str
    redacted: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}:{self.column}: {self.kind}: {self.redacted}"


def redact(value: str, keep: int = 1) -> str:
    """Show only the first `keep` characters, so a log line locates without leaking."""
    return value[:keep] + "*" * max(len(value) - keep, 2)


def load_terms(env: str | None, terms_file: Path) -> list[str]:
    raw = (env or "").replace(",", "\n").splitlines()
    if terms_file.is_file():
        raw += terms_file.read_text(encoding="utf-8").splitlines()
    terms = {t.strip() for t in raw if t.strip() and not t.strip().startswith("#")}
    return sorted(terms, key=lambda t: (-len(t), t))  # longest first, then stable


def _email_allowed(address: str, domain: str) -> bool:
    address, domain = address.lower(), domain.lower()
    return address in ALLOWED_EMAILS or any(
        domain == d or domain.endswith("." + d) for d in ALLOWED_EMAIL_DOMAINS
    )


def check_line(path: str, lineno: int, line: str, terms: list[str]) -> list[Finding]:
    if ALLOW_MARKER in line:
        return []
    out: list[Finding] = []

    def add(match: re.Match[str], kind: str, shown: str) -> None:
        out.append(Finding(path, lineno, match.start() + 1, kind, shown))

    for m in HOME_PATH.finditer(line):
        if m.group(1).lower() not in PLACEHOLDER_USERS:
            add(m, "home-path", m.group(0)[: m.start(1) - m.start()] + redact(m.group(1)))
    for m in PROJECT_SLUG.finditer(line):
        if m.group(1).lower() not in PLACEHOLDER_USERS:
            add(m, "project-slug", redact(m.group(1)))
    if not _NOT_AN_EMAIL.search(line):
        for m in EMAIL.finditer(line):
            if not _email_allowed(m.group(0), m.group(1)):
                add(m, "email", redact(m.group(0).split("@")[0]) + "@" + redact(m.group(1)))
    lowered = line.lower()
    for i, term in enumerate(terms, 1):
        for m in re.finditer(r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)", lowered):
            add(m, "private-term", f"<term #{i}>")
    return out


def check_file(path: Path, terms: list[str]) -> list[Finding]:
    if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:  # binary file
        return []
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        findings += check_line(str(path), lineno, line, terms)
    return findings


def tracked_files() -> list[Path]:
    result = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True, text=True)
    return [Path(p) for p in result.stdout.split("\0") if p]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    files = [Path(a) for a in args] if args else tracked_files()
    terms = load_terms(os.environ.get("PRIVATE_TERMS"), Path(TERMS_FILE))
    findings = [f for path in files for f in check_file(path, terms)]
    for f in findings:
        print(f)
    if findings:
        print(
            f"\n{len(findings)} possible private-data leak(s). Replace them with placeholders "
            f"(/home/u, -home-u-, someone@example.com), or add '{ALLOW_MARKER}' to the line "
            "if it is intended.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
