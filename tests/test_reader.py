import json
import multiprocessing as mp
import time

import transcripts as t

from tutor_agent import reader
from tutor_agent.events import Kind


def main_path(tmp_path):
    return tmp_path / "projects/-home-u-proj" / f"{t.SESSION}.jsonl"


def prompts(batch):
    return [e.content for e in batch.events if e.kind is Kind.PROMPT]


def test_each_read_returns_only_new_events(tmp_path):
    path = t.write(main_path(tmp_path), t.turn(0))
    first = reader.read_new(path)
    assert prompts(first) == ["add caching #0"]
    assert (first.first_line, first.last_line) == (1, 8)
    assert first.events[0].transcript_ref == f"{path.resolve()}:1"

    assert reader.read_new(path).events == []

    t.write(path, t.turn(1), append=True)
    second = reader.read_new(path)
    assert prompts(second) == ["add caching #1"]
    assert (second.first_line, second.last_line) == (9, 16)


def test_partial_last_line_is_read_next_time(tmp_path):
    path = t.write(main_path(tmp_path), t.turn(0), partial='{"type": "user", "mess')
    assert len(reader.read_new(path).events) == 6
    with path.open("a") as f:
        f.write('age": {"content": "next prompt"}}\n')
    assert prompts(reader.read_new(path)) == ["next prompt"]


def test_broken_complete_line_is_skipped_not_stuck(tmp_path):
    path = t.write(main_path(tmp_path), [t.prompt("a")])
    with path.open("a") as f:
        f.write("not json\n")
    t.write(path, [t.prompt("b")], append=True)
    batch = reader.read_new(path)
    assert prompts(batch) == ["a", "b"] and batch.skipped_lines == 1


def test_dry_run_keeps_the_offset(tmp_path):
    path = t.write(main_path(tmp_path), t.turn(0))
    assert len(reader.read_new(path, advance=False).events) == 6
    assert len(reader.read_new(path).events) == 6


def test_shrunk_transcript_is_read_from_the_start(tmp_path):
    path = t.write(main_path(tmp_path), t.turn(0) + t.turn(1))
    reader.read_new(path)
    t.write(path, [t.prompt("fresh")])
    assert prompts(reader.read_new(path)) == ["fresh"]


def test_subagent_has_its_own_offset_in_the_session_file(tmp_path, data_dir):
    main = t.write(main_path(tmp_path), t.turn(0))
    sub = t.write(main.with_suffix("") / "subagents/agent-ab12.jsonl", t.turn(5, agent_id="ab12"))
    assert reader.session_id_for(sub) == t.SESSION

    batch = reader.read_new(sub)
    assert prompts(batch) == ["add caching #5"] and {e.agent_id for e in batch.events} == {"ab12"}
    assert prompts(reader.read_new(main)) == ["add caching #0"]

    offsets = json.loads((data_dir / "offsets" / f"{t.SESSION}.json").read_text())
    assert set(offsets) == {str(main.resolve()), str(sub.resolve())}


def test_backlog_keeps_newest_events(tmp_path, monkeypatch):
    monkeypatch.setattr(reader, "MAX_EVENTS", 6)
    path = t.write(main_path(tmp_path), t.turn(0) + t.turn(1) + t.turn(2))
    batch = reader.read_new(path)
    assert prompts(batch) == ["add caching #2"] and batch.dropped_events == 12


def test_unsafe_session_id_is_refused(tmp_path):
    path = t.write(main_path(tmp_path), t.turn(0))
    try:
        reader.read_new(path, "../evil")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def _reader_proc(path, data_dir, out):
    import os

    os.environ["TUTOR_AGENT_DATA_DIR"] = str(data_dir)
    reader.MAX_EVENTS = 10**6  # this test is about locking, not the backlog cap
    for _ in range(20):
        batch = reader.read_new(path)
        out.put([e.content for e in batch.events if e.kind is Kind.PROMPT])
        time.sleep(0.02)  # spread the reads over the writing period


def test_concurrent_readers_never_read_a_line_twice(tmp_path, data_dir, monkeypatch):
    """Two hooks firing at once (e.g. Stop twice) while the agent keeps writing."""
    monkeypatch.setattr(reader, "MAX_EVENTS", 10**6)
    path = t.write(main_path(tmp_path), [])
    ctx = mp.get_context("spawn")
    out = ctx.Queue()
    procs = [ctx.Process(target=_reader_proc, args=(path, data_dir, out)) for _ in range(4)]
    for p in procs:
        p.start()
    for n in range(50):
        t.write(path, t.turn(n), append=True)
        time.sleep(0.01)  # let reads interleave with writes
    for p in procs:
        p.join()
    seen = [c for _ in range(80) for c in out.get()]
    seen += prompts(reader.read_new(path))  # whatever was written after the last process read
    assert sorted(seen) == sorted(f"add caching #{n}" for n in range(50))
