"""Detection quality on the M0 fixture batches with the real model. Six Haiku calls (about $0.03
at list price), so it only runs with `-m prompt`.

The model is not deterministic, so each batch checks loosely: at least one concept matches the
ideas the M0 spike runs found (Haiku and Sonnet, spike/results/detection-runs.json), and no
concept is a basic.
"""

import re
import shutil

import batches
import pytest

from tutor_agent import detector
from tutor_agent.events import Kind
from tutor_agent.settings import Settings

pytestmark = [
    pytest.mark.prompt,
    pytest.mark.skipif(shutil.which("claude") is None, reason="claude not installed"),
]

EXPECTED = {
    "harness-gates-python": r"infra|budget|timeout|baseline|preflight|fail.fast|limit|backstop",
    "ics-meeting-widget": r"subprocess|process boundary|helper process|error.as.data|recurrence|test double|stub|PATH|mature library|degradation",
    "qml-animation-widget": r"binding|declarative|reactive|animation|layer.shell|polling",
    "subagent": r"snapshot|diff|glob|escap|probe|schema",
    "supervisor-loop": r"rollback|checkpoint|canary|watchdog|supervisor|allowlist|least.privilege|exit code|retry",
}
BASICS = re.compile(
    r"\b(for loops?|if statements?|variables?|assignment|string formatting|f-strings?|print(ing)?|"
    r"comments?|renam(e|ing)|formatting|imports?)\b",
    re.I,
)


def detect(name: str, known: list[str]):
    return detector.detect(batches.load(name), known, Settings())


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_finds_expected_concepts_and_no_basics(name):
    found = detect(name, [])
    names = [c.name for c in found]
    print(name, [(c.name, c.category, c.event.kind) for c in found])
    assert 1 <= len(found) <= detector.MAX_CONCEPTS
    assert any(re.search(EXPECTED[name], n, re.I) for n in names), names
    assert not any(BASICS.fullmatch(n.strip()) for n in names), names
    assert all(not c.reuses_known for c in found)


def test_points_at_code_not_at_prose():
    """M6 regression: on this real batch, the snippets were a `cat` output and a test diff, while
    the concepts were written in edits to the main code (ADR 0030)."""
    events = batches.load("tutor-store-and-pane")
    found = detector.detect(events, [], Settings())
    print([(c.name, events.index(c.event), c.event.kind, c.event.file) for c in found])
    assert found
    picked = [c.event for c in found]
    assert all(e.kind in (Kind.EDIT, Kind.COMMAND, Kind.TOOL_RESULT) for e in picked)
    assert any(e.kind is Kind.EDIT for e in picked)
    assert not any("/docs/" in (e.file or "") for e in picked)
    # A test file is the right source only for a testing concept.
    assert not any("/tests/" in (c.event.file or "") and c.category != "Testing" for c in found)


def test_reuses_a_known_name_instead_of_a_near_duplicate():
    known = "Last-known-good rollback"
    found = detect("supervisor-loop", [known, "Retry with backoff"])
    print([(c.name, c.reuses_known) for c in found])
    for c in found:
        if re.search(r"rollback|last.known.good", c.name, re.I):
            assert c.reuses_known and c.name == known
