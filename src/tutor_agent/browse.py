"""What the tutor pane lists: status tabs, search, filters, and sort (ADR 0035).

Pure functions over concepts, so they are tested without Textual. `tui.py` wires them to widgets.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from tutor_agent.store import Concept, Status


class Sort(StrEnum):
    NEWEST = "newest"
    OLDEST = "oldest"
    MOST_SEEN = "most seen"
    NAME = "A–Z"  # noqa: RUF001  # the en dash is intended


# One tab per status, then All (None). The pane opens on the first one.
TABS: tuple[Status | None, ...] = (
    Status.NEW,
    Status.SEEN,
    Status.UNDERSTOOD,
    Status.DISMISSED,
    None,
)

ICONS: dict[Status, str] = {
    Status.NEW: "●",
    Status.SEEN: "◐",
    Status.UNDERSTOOD: "✓",
    Status.DISMISSED: "✗",
}

STYLES: dict[Status, str] = {
    Status.NEW: "bold yellow",
    Status.SEEN: "cyan",
    Status.UNDERSTOOD: "green",
    Status.DISMISSED: "red",
}


def tab_id(tab: Status | None) -> str:
    return f"tab-{tab or 'all'}"


def tab_title(tab: Status | None) -> str:
    return str(tab).capitalize() if tab else "All"


def project_name(concept: Concept) -> str:
    project = concept.sources[-1].project if concept.sources else None
    return project.rstrip("/").rsplit("/", 1)[-1] if project else "?"


@dataclass(frozen=True)
class Filters:
    query: str = ""
    project: str | None = None
    category: str | None = None
    sort: Sort = Sort.NEWEST

    @property
    def active(self) -> bool:
        return self != Filters()

    def next_sort(self) -> Filters:
        order = list(Sort)
        return replace(self, sort=order[(order.index(self.sort) + 1) % len(order)])

    def chips(self) -> str:
        """The filter line above the list, e.g. `/ lock · project: api · sort: A–Z`."""  # noqa: RUF002
        parts = []
        if self.query:
            parts.append(f"/ {self.query}")
        if self.project:
            parts.append(f"project: {self.project}")
        if self.category:
            parts.append(f"category: {self.category}")
        parts.append(f"sort: {self.sort}")
        return " · ".join(parts)


def fuzzy(query: str, text: str) -> bool:
    """True if the letters of `query` appear in `text` in order, ignoring case and spaces."""
    it = iter(text.lower())
    return all(ch in it for ch in query.lower() if not ch.isspace())


def matches(concept: Concept, filters: Filters) -> bool:
    q = filters.query.strip()
    if q and not (fuzzy(q, concept.name) or q.lower() in concept.summary.lower()):
        return False
    if filters.project is not None and project_name(concept) != filters.project:
        return False
    return filters.category is None or concept.category == filters.category


def sort(concepts: list[Concept], by: Sort) -> list[Concept]:
    # Ties keep a stable, readable order: by name.
    by_name = sorted(concepts, key=lambda c: c.name.lower())
    if by is Sort.NAME:
        return by_name
    if by is Sort.MOST_SEEN:
        return sorted(by_name, key=lambda c: len(c.sources), reverse=True)
    return sorted(by_name, key=lambda c: c.created_at, reverse=by is Sort.NEWEST)


def visible(concepts: list[Concept], tab: Status | None, filters: Filters) -> list[Concept]:
    """The concepts in `tab` (None = All) that pass the filters, in the chosen order."""
    shown = [c for c in concepts if (tab is None or c.status is tab) and matches(c, filters)]
    return sort(shown, filters.sort)


def counts(concepts: list[Concept], filters: Filters) -> dict[Status | None, int]:
    """Concepts per tab after the filters, for the tab labels."""
    kept = [c for c in concepts if matches(c, filters)]
    out: dict[Status | None, int] = dict.fromkeys(TABS, 0)
    for c in kept:
        out[c.status] += 1
    out[None] = len(kept)
    return out


def projects(concepts: list[Concept]) -> list[str]:
    return sorted({project_name(c) for c in concepts}, key=str.lower)


def categories(concepts: list[Concept]) -> list[str]:
    return sorted({c.category for c in concepts}, key=str.lower)
