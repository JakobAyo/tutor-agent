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


def _tui(args) -> int:
    from tutor_agent import tui

    return tui.main()


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(prog="tutor", description="Learn the concepts behind your Claude Code sessions.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("hook", help="Claude Code hook entry (reads the hook JSON on stdin)").set_defaults(func=_hook)

    detect = sub.add_parser("detect", help="find concepts in the new part of a transcript")
    detect.add_argument("transcript", help="transcript JSONL (main session or subagent)")
    detect.add_argument("--session-id", help="defaults to the id in the transcript path")
    detect.add_argument("--dry-run", action="store_true", help="log the batch instead of detecting; keeps the offset")
    detect.set_defaults(func=_detect)

    for name, text in (("install", "add the tutor hook to ~/.claude/settings.json"),
                       ("uninstall", "remove the tutor hook from ~/.claude/settings.json")):
        p = sub.add_parser(name, help=text)
        p.add_argument("-y", "--yes", action="store_true", help="don't ask before writing")
        p.set_defaults(func=_install)

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
