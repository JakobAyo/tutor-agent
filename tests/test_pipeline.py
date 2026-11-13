"""`tutor detect` end to end on a synthetic transcript, with the fake `claude` and `notify-send`."""

import transcripts as t

from tutor_agent import cli, paths
from tutor_agent.store import ConceptStore, Source, Status

EDIT_INDEX = 2  # in t.turn(): prompt, reasoning, edit, command, tool_result, reasoning


def found(name="LRU caching", *, reuses_known=False, event_index=EDIT_INDEX, category="Design patterns"):
    return {"name": name, "category": category, "summary": "Keep the most recent results.",
            "why_here": "The agent cached lookups.", "event_index": event_index, "reuses_known": reuses_known}


def run_detect(tmp_path, n=0, append=False) -> int:
    path = t.write(tmp_path / f"{t.SESSION}.jsonl", t.turn(n), append=append)
    return cli.main(["detect", str(path)])


def known(name, status=Status.NEW):
    store = ConceptStore()
    store.add(name, "Testing", "old summary", Source(snippet="old", context="old"))
    if status is not Status.NEW:
        store.set_status(store.list()[0].id, status)


def titles(fake_notify):
    return [argv[-1] for argv in fake_notify.calls]


def test_new_concept_is_stored_with_snippet_and_notified(tmp_path, fake_claude, fake_notify):
    fake_claude.answer({"concepts": [found()]})
    assert run_detect(tmp_path) == 0
    [c] = ConceptStore().list()
    assert (c.name, c.category, c.status) == ("LRU caching", "Design patterns", Status.NEW)
    [src] = c.sources
    assert src.snippet == "--- old\nx\n+++ new\ny"
    assert src.context == "The agent cached lookups."
    assert (src.project, src.session_id, src.file) == ("/home/u/proj", t.SESSION, "/home/u/proj/a.py")
    assert src.kind == "edit"
    assert src.transcript_ref.endswith(f"{t.SESSION}.jsonl:4")
    assert titles(fake_notify) == ["• LRU caching (Design patterns)"]


def test_known_concept_gets_a_source_and_no_notification(tmp_path, fake_claude, fake_notify):
    known("LRU caching", Status.UNDERSTOOD)
    fake_claude.answer({"concepts": [found("lru caching", reuses_known=True)]})
    run_detect(tmp_path)
    [c] = ConceptStore().list()
    assert c.status is Status.UNDERSTOOD and c.summary == "old summary"
    assert [s.snippet for s in c.sources] == ["old", "--- old\nx\n+++ new\ny"]
    assert fake_notify.calls == []


def test_dismissed_concept_is_skipped(tmp_path, fake_claude, fake_notify):
    known("LRU caching", Status.DISMISSED)
    fake_claude.answer({"concepts": [found(reuses_known=True)]})
    run_detect(tmp_path)
    assert len(ConceptStore().list()[0].sources) == 1
    assert fake_notify.calls == []
    assert "LRU caching" in fake_claude.record["stdin"].splitlines()[0]  # dismissed names are KNOWN


def test_renamed_known_concept_is_dropped(tmp_path, fake_claude, fake_notify):
    known("LRU caching")
    fake_claude.answer({"concepts": [found("Least-recently-used cache", reuses_known=True)]})
    run_detect(tmp_path)
    assert [c.id for c in ConceptStore().list()] == ["lru-caching"]
    assert fake_notify.calls == []
    assert "matches no known name" in paths.log_file().read_text()


def test_same_concept_twice_in_a_batch_is_stored_once(tmp_path, fake_claude, fake_notify):
    fake_claude.answer({"concepts": [found(), found("LRU Caching", event_index=1), found("Fakes", category="Testing")]})
    run_detect(tmp_path)
    store = ConceptStore()
    assert sorted(c.id for c in store.list()) == ["fakes", "lru-caching"]
    assert len(store.get("lru-caching").sources) == 1
    assert titles(fake_notify) == ["• LRU caching (Design patterns)\n• Fakes (Testing)"]


def test_one_call_and_one_notification_per_turn(tmp_path, fake_claude, fake_notify):
    fake_claude.answer({"concepts": [found(), found("Fakes", category="Testing")]})
    run_detect(tmp_path)
    run_detect(tmp_path, append=True, n=1)  # nothing new on the transcript, then a second turn
    path = tmp_path / f"{t.SESSION}.jsonl"
    cli.main(["detect", str(path)])  # no new lines: pre-filter skip, no call
    assert fake_claude.calls == 2
    assert len(fake_notify.calls) == 1  # the second turn found only known concepts


def test_mute_stores_but_does_not_notify(tmp_path, fake_claude, fake_notify):
    paths.settings_file().write_text("muted = true\n")
    fake_claude.answer({"concepts": [found()]})
    run_detect(tmp_path)
    assert len(ConceptStore().list()) == 1
    assert fake_notify.calls == []


def test_nothing_found_means_no_notification(tmp_path, fake_claude, fake_notify):
    fake_claude.answer({"concepts": []})
    assert run_detect(tmp_path) == 0
    assert ConceptStore().list() == [] and fake_notify.calls == []
    assert "nothing" in paths.log_file().read_text()


def test_failed_call_stores_nothing_and_is_logged(tmp_path, fake_claude, fake_notify):
    fake_claude.mode("fail")
    assert run_detect(tmp_path) == 1
    assert ConceptStore().list() == [] and fake_notify.calls == []
    assert "detect failed" in paths.log_file().read_text()


def test_invalid_output_stores_nothing(tmp_path, fake_claude, fake_notify):
    fake_claude.answer({"concepts": [found(event_index=99)]})
    assert run_detect(tmp_path) == 0
    assert ConceptStore().list() == [] and fake_notify.calls == []
