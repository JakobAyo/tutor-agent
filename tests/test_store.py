import json
import multiprocessing as mp

import pytest

from tutor_agent import paths
from tutor_agent.store import ConceptStore, Entry, Outcome, Source, Status, StoreError, concept_id


def src(text="x = 1", context="the agent did a thing"):
    return Source(
        snippet=text, context=context, project="~/p", session_id="s1", transcript_ref="t.jsonl:3"
    )


def test_concept_id_normalizes_names():
    assert (
        concept_id("Dependency Injection")
        == concept_id("dependency-injection")
        == "dependency-injection"
    )
    with pytest.raises(ValueError):
        concept_id("  !! ")


def test_add_and_reload():
    store = ConceptStore()
    concept, outcome = store.add(
        "Atomic file writes", "mechanism", "Write to temp, then rename.", src()
    )
    assert outcome is Outcome.CREATED and concept.status is Status.NEW
    loaded = ConceptStore().get("atomic-file-writes")
    assert loaded == concept
    assert loaded.sources[0].snippet == "x = 1"


def test_adding_existing_name_attaches_source():
    store = ConceptStore()
    store.add("Retry with backoff", "pattern", "s", src("a"))
    concept, outcome = store.add("retry with backoff", "pattern", "other summary", src("b"))
    assert outcome is Outcome.ATTACHED
    assert concept.summary == "s"
    assert [s.snippet for s in concept.sources] == ["a", "b"]
    assert len(store.list()) == 1


def test_dismissed_concept_gets_no_new_source():
    store = ConceptStore()
    store.add("Idempotency", "pattern", "s", src("a"))
    store.set_status("idempotency", Status.DISMISSED)
    concept, outcome = store.add("idempotency", "pattern", "s", src("b"))
    assert outcome is Outcome.DISMISSED
    assert [s.snippet for s in store.get("idempotency").sources] == ["a"]


def test_record_stores_a_batch_in_one_write():
    store = ConceptStore()
    store.add("Known", "pattern", "s", src("a"))
    results = store.record(
        [Entry("New one", "pattern", "s", src("b")), Entry("known", "pattern", "s", src("c"))]
    )
    assert [o for _, o in results] == [Outcome.CREATED, Outcome.ATTACHED]
    assert len(store.get("known").sources) == 2


def test_status_changes():
    store = ConceptStore()
    store.add("Idempotency", "pattern", "s", src())
    assert store.mark_seen("idempotency").status is Status.SEEN
    assert store.set_status("idempotency", Status.UNDERSTOOD).status is Status.UNDERSTOOD
    assert store.mark_seen("idempotency").status is Status.UNDERSTOOD  # never downgraded
    assert store.set_status("idempotency", "dismissed").status is Status.DISMISSED
    with pytest.raises(ValueError):
        store.set_status("idempotency", "bogus")


def test_unknown_concept_raises():
    with pytest.raises(KeyError):
        ConceptStore().set_status("nope", Status.SEEN)


def test_failed_change_saves_nothing():
    store = ConceptStore()
    store.add("Idempotency", "pattern", "s", src())
    before = store.path.read_text()
    with pytest.raises(ValueError):
        store.set_status("idempotency", "bogus")
    assert store.path.read_text() == before


def test_corrupt_file_is_never_overwritten():
    path = paths.concepts_file()
    path.write_text("{not json")
    store = ConceptStore()
    with pytest.raises(StoreError):
        store.add("x", "pattern", "s", src())
    assert path.read_text() == "{not json"


def test_no_temp_files_left_behind():
    store = ConceptStore()
    store.add("a", "pattern", "s", src())
    store.add("b", "pattern", "s", src())
    leftovers = [p.name for p in store.path.parent.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


def _writer(data_dir: str, worker: int, n: int) -> None:
    import os

    os.environ["TUTOR_AGENT_DATA_DIR"] = data_dir
    store = ConceptStore()
    for i in range(n):
        store.add(f"concept {worker}-{i}", "pattern", "s", src(f"w{worker} i{i}"))
        store.add("shared concept", "pattern", "s", src(f"w{worker} i{i}"))


def test_parallel_writers_lose_nothing(data_dir):
    workers, per_worker = 8, 25
    ctx = mp.get_context("spawn")  # fresh interpreters, like separate detector processes
    procs = [
        ctx.Process(target=_writer, args=(str(data_dir), w, per_worker)) for w in range(workers)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)
        assert p.exitcode == 0

    raw = json.loads(paths.concepts_file().read_text())  # still valid JSON
    concepts = {c["id"]: c for c in raw["concepts"]}
    assert len(concepts) == workers * per_worker + 1
    shared = concepts["shared-concept"]["sources"]
    assert len(shared) == workers * per_worker
    assert len({s["snippet"] for s in shared}) == workers * per_worker
