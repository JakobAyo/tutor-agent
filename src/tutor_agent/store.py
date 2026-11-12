"""The concept memory: one JSON file, changed only under a file lock and replaced atomically.

Readers never take the lock. `os.replace` swaps the file in one step, so a reader sees either
the old or the new version, never a half-written one. Writers take an exclusive `flock` on a
separate lock file, so two processes can't both read version N and overwrite each other's change.
"""

import fcntl
import json
import os
import re
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from tutor_agent import paths

FORMAT_VERSION = 1


class Status(StrEnum):
    NEW = "new"
    SEEN = "seen"
    UNDERSTOOD = "understood"
    DISMISSED = "dismissed"


class StoreError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def concept_id(name: str) -> str:
    """Stable key for a concept name: "Dependency Injection" and "dependency-injection" match."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError(f"concept name has no letters or digits: {name!r}")
    return slug


@dataclass
class Source:
    """Where a concept appeared. The snippet is stored so lessons outlive the transcript (ADR 0013)."""

    snippet: str
    context: str
    project: str | None = None
    session_id: str | None = None
    transcript_ref: str | None = None
    file: str | None = None
    seen_at: str = field(default_factory=now)


@dataclass
class Concept:
    id: str
    name: str
    category: str
    summary: str
    status: Status = Status.NEW
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    sources: list[Source] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict) -> "Concept":
        return cls(**{**raw, "status": Status(raw["status"]), "sources": [Source(**s) for s in raw["sources"]]})


class ConceptStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or paths.concepts_file()
        self.lock_path = self.path.with_name(self.path.name + ".lock")

    def list(self) -> list[Concept]:
        return list(self._load().values())

    def get(self, cid: str) -> Concept | None:
        return self._load().get(cid)

    def add(self, name: str, category: str, summary: str, source: Source) -> tuple[Concept, bool]:
        """Add a concept, or attach the source if it already exists. Returns (concept, created)."""
        cid = concept_id(name)
        with self._transaction() as concepts:
            existing = concepts.get(cid)
            if existing:
                existing.sources.append(source)
                existing.updated_at = now()
                return existing, False
            concept = Concept(id=cid, name=name, category=category, summary=summary, sources=[source])
            concepts[cid] = concept
            return concept, True

    def add_source(self, cid: str, source: Source) -> Concept:
        with self._transaction() as concepts:
            concept = self._require(concepts, cid)
            concept.sources.append(source)
            concept.updated_at = now()
            return concept

    def set_status(self, cid: str, status: Status) -> Concept:
        with self._transaction() as concepts:
            concept = self._require(concepts, cid)
            concept.status = Status(status)
            concept.updated_at = now()
            return concept

    def mark_seen(self, cid: str) -> Concept:
        """Opening a lesson moves `new` to `seen`. It never downgrades `understood` or `dismissed`."""
        with self._transaction() as concepts:
            concept = self._require(concepts, cid)
            if concept.status is Status.NEW:
                concept.status = Status.SEEN
                concept.updated_at = now()
            return concept

    @staticmethod
    def _require(concepts: dict[str, Concept], cid: str) -> Concept:
        if cid not in concepts:
            raise KeyError(f"unknown concept: {cid}")
        return concepts[cid]

    @contextmanager
    def _transaction(self) -> Iterator[dict[str, Concept]]:
        """Lock, load, let the caller change the dict, save. Nothing is saved if the caller raises."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_path, "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                concepts = self._load()
                yield concepts
                self._save(concepts)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _load(self) -> dict[str, Concept]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            raise StoreError(f"{self.path} is not valid JSON, refusing to touch it: {e}") from e
        if raw.get("version") != FORMAT_VERSION:
            raise StoreError(f"{self.path}: unsupported format version {raw.get('version')!r}")
        return {c["id"]: Concept.from_dict(c) for c in raw["concepts"]}

    def _save(self, concepts: dict[str, Concept]) -> None:
        payload = {"version": FORMAT_VERSION, "concepts": [asdict(c) for c in concepts.values()]}
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=self.path.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=1, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
