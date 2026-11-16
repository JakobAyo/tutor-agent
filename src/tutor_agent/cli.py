"""The `tutor` command. Imports stay inside the handlers, so `tutor hook` starts fast."""

import sys


def _hook(args) -> int:
    from tutor_agent import hook

    return hook.main()


def _detect(args) -> int:
    from pathlib import Path

    from tutor_agent import paths, pipeline

    code = pipeline.process(Path(args.transcript), args.session_id, dry_run=args.dry_run)
    if args.dry_run:
        print(f"Dry run done, see {paths.log_file()}")
    return code


def _install(args) -> int:
    from tutor_agent import install

    try:
        (install.uninstall if args.command == "uninstall" else install.install)(assume_yes=args.yes)
    except install.InstallError as e:
        print(f"tutor: {e}", file=sys.stderr)
        return 1
    return 0


def _explain(args) -> int:
    from tutor_agent import explain, followups, runner, settings
    from tutor_agent.store import ConceptStore, StoreError

    sessions = explain.recent_sessions()
    if args.list or not sessions:
        for i, s in enumerate(sessions, 1):
            print(f"{i:>2}. {s.label()}")
        if not sessions:
            print("tutor: no Claude Code sessions found", file=sys.stderr)
        return 0 if sessions else 1
    if not 1 <= args.pick <= len(sessions):
        print(f"tutor: pick a number from 1 to {len(sessions)} (see --list)", file=sys.stderr)
        return 1
    session = sessions[args.pick - 1]
    try:
        known = followups.known_concepts(ConceptStore().list())
        text = explain.explain(explain.latest_turn(session), known, settings.load())
    except (
        OSError,
        StoreError,
        settings.SettingsError,
        runner.ClaudeError,
        explain.ExplainError,
    ) as e:
        print(f"tutor: {e}", file=sys.stderr)
        return 1
    print(f"{session.label()}\n\n{text}")
    return 0


def _stats(args) -> int:
    from collections import Counter

    from tutor_agent import paths, usage
    from tutor_agent.store import ConceptStore, StoreError

    try:
        concepts = ConceptStore().list()
    except StoreError as e:
        print(f"tutor: {e}", file=sys.stderr)
        return 1
    path = paths.concepts_file()
    size = path.stat().st_size if path.exists() else 0
    by_status = Counter(str(c.status) for c in concepts)
    sources = sum(len(c.sources) for c in concepts)
    lessons = len(list(paths.lessons_dir().glob("*.json"))) if paths.lessons_dir().exists() else 0
    print(f"Concept memory: {len(concepts)} concepts, {sources} sources, {size / 1024:.1f} KB")
    print(
        "  "
        + ", ".join(
            f"{s}: {by_status.get(s, 0)}" for s in ("new", "seen", "understood", "dismissed")
        )
    )
    print(f"Cached lessons: {lessons}")

    days = list(usage.per_day().items())[-args.days :]
    print(f"\nUsage per day (last {args.days} days with calls):")
    if not days:
        print("  no calls recorded yet")
    for date, d in days:
        jobs = ", ".join(f"{job} {n}" for job, n in sorted(d.calls.items()))
        failed = f", {d.failed} failed" if d.failed else ""
        print(
            f"  {date}  {sum(d.calls.values()):>3} calls ({jobs}{failed})  ${d.cost_usd:.3f}  {d.ms / 1000:.0f}s"
        )
    return 0


def _tui(args) -> int:
    from tutor_agent import tui

    return tui.main()


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="tutor", description="Learn the concepts behind your Claude Code sessions."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "hook", help="Claude Code hook entry (reads the hook JSON on stdin)"
    ).set_defaults(func=_hook)

    detect = sub.add_parser("detect", help="find concepts in the new part of a transcript")
    detect.add_argument("transcript", help="transcript JSONL (main session or subagent)")
    detect.add_argument("--session-id", help="defaults to the id in the transcript path")
    detect.add_argument(
        "--dry-run",
        action="store_true",
        help="log the batch instead of detecting; keeps the offset",
    )
    detect.set_defaults(func=_detect)

    for name, text in (
        ("install", "add the tutor hook to ~/.claude/settings.json"),
        ("uninstall", "remove the tutor hook from ~/.claude/settings.json"),
    ):
        p = sub.add_parser(name, help=text)
        p.add_argument("-y", "--yes", action="store_true", help="don't ask before writing")
        p.set_defaults(func=_install)

    explain = sub.add_parser(
        "explain", help="explain what just happened in a recent session (one model call)"
    )
    explain.add_argument(
        "pick",
        nargs="?",
        type=int,
        default=1,
        help="session number from --list (default 1: the most recently active)",
    )
    explain.add_argument(
        "--list", action="store_true", help="list the recent sessions, no model call"
    )
    explain.set_defaults(func=_explain)

    stats = sub.add_parser(
        "stats", help="concept memory size and model usage per day (no model call)"
    )
    stats.add_argument(
        "--days", type=int, default=14, help="how many days with calls to show (default 14)"
    )
    stats.set_defaults(func=_stats)

    sub.add_parser("tui", help="open the tutor pane").set_defaults(func=_tui)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["hook"]:  # fast path: skip argparse, it runs inside every agent turn
        return _hook(None)
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
