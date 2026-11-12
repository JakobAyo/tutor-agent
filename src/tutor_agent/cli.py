"""The `tutor` command. Imports stay inside the handlers, so `tutor hook` starts fast."""

import argparse
import os
import sys


def _hook(args: argparse.Namespace) -> int:
    # Recursion guard, layer 2 (ADR 0022). Must stay the first thing the hook does.
    if os.environ.get("TUTOR_AGENT_INTERNAL") == "1":
        return 0
    sys.stdin.read()  # M2: parse the payload and start `tutor detect` detached.
    return 0


def _detect(args: argparse.Namespace) -> int:
    print("tutor detect: not implemented yet (M2/M3)")
    return 0


def _tui(args: argparse.Namespace) -> int:
    print("tutor tui: not implemented yet (M4)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tutor", description="Learn the concepts behind your Claude Code sessions.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("hook", help="Claude Code hook entry (reads the hook JSON on stdin)").set_defaults(func=_hook)
    sub.add_parser("detect", help="find concepts in new transcript events").set_defaults(func=_detect)
    sub.add_parser("tui", help="open the tutor pane").set_defaults(func=_tui)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
