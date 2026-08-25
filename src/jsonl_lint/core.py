"""Validation primitives for JSONL files.

A JSONL file is one JSON value per line. That sounds simple enough that most
projects validate it with ``json.loads`` in a loop, which reports the first
failure and stops. When the file is a training or eval set of tens of
thousands of lines, "line 8,412 is bad" one line at a time is a slow way to
find out that 300 lines are bad.

Everything here collects *all* problems and keeps going.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator

#: A byte-order mark on the first line is the single most common cause of a
#: JSONL file that "looks fine" in an editor but fails to parse.
BOM = "\ufeff"


@dataclass(frozen=True)
class Problem:
    """One thing wrong with one line.

    ``line`` is 1-based, matching what an editor and a traceback both show.
    """

    line: int
    code: str
    message: str

    def __str__(self) -> str:
        return f"line {self.line}: {self.code}: {self.message}"


@dataclass
class Report:
    """The outcome of checking a file."""

    problems: list[Problem] = field(default_factory=list)
    records: int = 0

    @property
    def ok(self) -> bool:
        return not self.problems

    def codes(self) -> dict[str, int]:
        """How many times each problem code fired, for a summary line."""
        counts: dict[str, int] = {}
        for problem in self.problems:
            counts[problem.code] = counts.get(problem.code, 0) + 1
        return counts


def iter_problems(lines: Iterable[str], *, require_object: bool = False) -> Iterator[Problem]:
    """Yield a :class:`Problem` for every defect in ``lines``.

    ``lines`` is any iterable of strings with or without trailing newlines, so
    a file object, a list, or a generator all work.

    :param require_object: also reject lines that parse but are not JSON
        objects. Most JSONL consumers -- fine-tuning APIs especially -- accept
        only objects, but the format itself permits any JSON value, so this is
        opt-in.
    """
    for number, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n").rstrip("\r")

        if number == 1 and line.startswith(BOM):
            yield Problem(number, "bom", "file starts with a UTF-8 byte-order mark")
            line = line[len(BOM) :]

        if not line.strip():
            yield Problem(number, "blank", "line is empty or whitespace only")
            continue

        if line != line.strip():
            yield Problem(number, "whitespace", "line has leading or trailing whitespace")

        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            yield Problem(number, "invalid-json", f"{error.msg} at column {error.colno}")
            continue

        if require_object and not isinstance(value, dict):
            kind = type(value).__name__
            yield Problem(number, "not-an-object", f"line is a JSON {kind}, not an object")


def check(lines: Iterable[str], *, require_object: bool = False) -> Report:
    """Check ``lines`` and return a :class:`Report`.

    Counts every non-blank line as a record, whether or not it parsed, so the
    count reflects the file as written rather than as salvaged.
    """
    report = Report()
    materialised = list(lines)

    report.problems = list(iter_problems(materialised, require_object=require_object))
    report.records = sum(1 for raw in materialised if raw.strip())
    return report


def load(lines: Iterable[str]) -> Iterator[Any]:
    """Yield the parsed value of every line, skipping blanks.

    Raises :class:`json.JSONDecodeError` on the first bad line -- use
    :func:`check` first if you want the full picture.
    """
    for raw in lines:
        line = raw.lstrip(BOM).strip()
        if line:
            yield json.loads(line)
