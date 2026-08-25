"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from jsonl_lint import __version__
from jsonl_lint.core import Report, check

EXIT_OK = 0
EXIT_PROBLEMS = 1
EXIT_USAGE = 2
#: A file that could not be read is worse news than a file with bad content:
#: it means the run did not check what the caller thought it checked. It gets
#: its own code so CI can tell "your dataset is broken" from "your path is
#: wrong" without scraping stderr.
EXIT_IO = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jsonl-lint",
        description="Report every malformed line in a JSONL file, not just the first.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        metavar="FILE",
        help="files to check; reads stdin when omitted or when FILE is '-'",
    )
    parser.add_argument(
        "--require-object",
        action="store_true",
        help="also reject lines that parse but are not JSON objects",
    )
    parser.add_argument(
        "--check-duplicates",
        action="store_true",
        help="also report records that repeat an earlier line, ignoring key order",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="print nothing; signal the result through the exit code only",
    )
    parser.add_argument(
        "--max-problems",
        type=int,
        default=0,
        metavar="N",
        help="print at most N problems per file (0 means all)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _render(label: str, report: Report, *, max_problems: int, stream) -> None:
    shown = report.problems if max_problems <= 0 else report.problems[:max_problems]
    for problem in shown:
        print(f"{label}:{problem}", file=stream)

    hidden = len(report.problems) - len(shown)
    if hidden > 0:
        print(f"{label}: ... and {hidden} more", file=stream)

    summary = ", ".join(f"{code}={count}" for code, count in sorted(report.codes().items()))
    print(
        f"{label}: {report.records} records, {len(report.problems)} problems"
        + (f" ({summary})" if summary else ""),
        file=stream,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    paths = args.paths or ["-"]
    failed = False
    io_failed = False

    for path in paths:
        try:
            if path == "-":
                report = check(
                    sys.stdin,
                    require_object=args.require_object,
                    check_duplicates=args.check_duplicates,
                )
                label = "<stdin>"
            else:
                # newline="" keeps \r visible so a CRLF file is reported rather
                # than silently normalised by universal newline translation.
                with open(path, encoding="utf-8", newline="") as handle:
                    report = check(
                        handle,
                        require_object=args.require_object,
                        check_duplicates=args.check_duplicates,
                    )
                label = path
        except OSError as error:
            print(f"jsonl-lint: {path}: {error.strerror}", file=sys.stderr)
            io_failed = True
            # Keep going: with a glob, one unreadable file should not hide
            # problems in the files that did open.
            continue

        if not report.ok:
            failed = True
        if not args.quiet:
            _render(label, report, max_problems=args.max_problems, stream=sys.stdout)

    if io_failed:
        return EXIT_IO
    return EXIT_PROBLEMS if failed else EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
