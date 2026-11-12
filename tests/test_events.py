import transcripts as t

from tutor_agent.events import MAX_CONTENT, EventMapper, Kind, edit_content, truncate


def kinds(records):
    m = EventMapper()
    return [e.kind for i, r in enumerate(records) for e in m.map(r, f"x:{i}")]


def test_turn_maps_to_expected_kinds():
    assert kinds(t.turn()) == [
        Kind.PROMPT, Kind.REASONING, Kind.EDIT, Kind.COMMAND, Kind.TOOL_RESULT, Kind.REASONING,
    ]


def test_event_fields():
    m = EventMapper()
    (e,) = m.map(t.assistant(t.tool_use("1", "Write", file_path="/p/f.py", content="print(1)"), agent_id="ag1"), "f.jsonl:7")
    assert (e.kind, e.file, e.content, e.agent_id, e.session_id, e.project, e.transcript_ref) == (
        Kind.EDIT, "/p/f.py", "print(1)", "ag1", t.SESSION, "/home/u/proj", "f.jsonl:7",
    )


def test_injected_user_records_are_not_prompts():
    records = [
        t.prompt("<command-name>/clear</command-name>"),
        t.prompt("<local-command-stdout></local-command-stdout>"),
        t.prompt("<task-notification>done</task-notification>"),
        t.prompt("real question", isMeta=True),
        t.prompt("   "),
    ]
    assert kinds(records) == []


def test_prompt_with_text_blocks():
    rec = t._base("user", message={"content": [{"type": "text", "text": "hi"}, {"type": "image"}]})
    assert kinds([rec]) == [Kind.PROMPT]


def test_only_bash_results_are_kept():
    records = [
        t.assistant(t.tool_use("r", "Read", file_path="/x")),
        t.tool_result("r", "file contents"),
        t.assistant(t.tool_use("b", "Bash", command="ls")),
        t.tool_result("b", "a b c"),
    ]
    assert kinds(records) == [Kind.COMMAND, Kind.TOOL_RESULT]


def test_unknown_and_odd_records_are_ignored():
    assert kinds([t.other("file-history-delta"), {"type": "assistant"}, {"type": "user", "message": "str"}, {}]) == []


def test_tool_result_cut_harder():
    m = EventMapper()
    m.map(t.assistant(t.tool_use("b", "Bash", command="cat big")), "x")
    (e,) = m.map(t.tool_result("b", "line\n" * 1000), "x")
    assert len(e.content) < 900 and "chars cut" in e.content


def test_truncate_keeps_whole_lines_from_both_ends():
    text = "".join(f"line {i:04d}\n" for i in range(1000))
    out = truncate(text, 200)
    assert out.startswith("line 0000\n") and out.endswith("line 0999\n")
    assert all(len(l) == 9 or "cut" in l for l in out.splitlines())


def test_truncate_one_giant_line():
    out = truncate("x" * 5000, 100)
    assert len(out) < 200 and "chars cut" in out


def test_edit_short_is_full_diff():
    assert edit_content("Edit", {"old_string": "a", "new_string": "b"}) == "--- old\na\n+++ new\nb"


def test_multiedit_over_limit_keeps_whole_new_hunks():
    func = "def f():\n" + "".join(f"    step_{i}()\n" for i in range(40)) + "    return 1\n"
    edits = [{"old_string": func, "new_string": func.replace("f()", f"f{i}()")} for i in range(6)]
    out = edit_content("MultiEdit", {"edits": edits})
    assert len(out) <= MAX_CONTENT + 100
    assert "--- old" not in out and "more hunks cut" in out
    # every kept function is complete, from signature to return
    assert out.count("def f") == out.count("    return 1")


def test_write_keeps_the_top_of_the_file():
    content = "import os\n" + "x = 1\n" * 1000
    out = edit_content("Write", {"content": content})
    assert out.startswith("import os\n") and "chars cut" in out and len(out) <= MAX_CONTENT + 50
