# jsonl-lint

Report **every** malformed line in a JSONL file, not just the first one.

`json.loads` in a loop stops at the first bad line. On a 40,000-line training set that
turns "this file is broken" into forty rounds of fix-one-line-and-rerun. `jsonl-lint`
reads the whole file and tells you everything that is wrong in one pass.

```console
$ jsonl-lint train.jsonl
train.jsonl:line 1: bom: file starts with a UTF-8 byte-order mark
train.jsonl:line 88: invalid-json: Expecting ',' delimiter at column 41
train.jsonl:line 512: blank: line is empty or whitespace only
train.jsonl:line 4001: invalid-json: Unterminated string starting at column 12
train.jsonl: 40213 records, 4 problems (blank=1, bom=1, invalid-json=2)
```

Zero dependencies. Python 3.9+.

## Install

```sh
pip install jsonl-lint
```

## Use

```sh
jsonl-lint train.jsonl                  # one file
jsonl-lint data/*.jsonl                 # many; every one is checked
cat train.jsonl | jsonl-lint            # or stdin
jsonl-lint --require-object train.jsonl # reject lines that aren't JSON objects
jsonl-lint --check-duplicates train.jsonl  # report repeated records
jsonl-lint --quiet train.jsonl          # exit code only, for CI
jsonl-lint --max-problems 20 big.jsonl  # cap the noise
```

| Exit code | Meaning |
| --- | --- |
| `0` | every file was clean |
| `1` | at least one file had problems |
| `2` | bad usage |
| `3` | a file could not be read |

`3` takes precedence over `1`: if any file failed to open, the run did not check what you
asked it to, which is more urgent than bad content in the files that did open. The other
files are still checked and still reported.

## What it checks

| Code | Meaning |
| --- | --- |
| `invalid-json` | the line is not parseable JSON, with the column from the decoder |
| `blank` | the line is empty or whitespace only |
| `bom` | the file begins with a UTF-8 byte-order mark |
| `whitespace` | the line has leading or trailing whitespace |
| `not-an-object` | the line parses but is not a JSON object — only with `--require-object` |
| `duplicate` | the record repeats an earlier line — only with `--check-duplicates` |

`--require-object` is opt-in because JSONL permits any JSON value per line, while most
consumers of it (fine-tuning and eval APIs in particular) accept only objects.

`--check-duplicates` compares the *parsed* value with `sort_keys`, so two records that
differ only in key order or insignificant whitespace are still reported as duplicates.
Lines that failed to parse are never treated as duplicates of one another. It holds one
fingerprint per distinct record in memory, so it costs roughly the size of the file.

A byte-order mark is only reported on line 1, where it is a real file-level artifact. One
appearing mid-file is a parse error, and is reported as such.

Trailing newlines — `\n` or `\r\n` — are never reported as whitespace problems, so a
CRLF file checks clean.

## As a library

```python
from jsonl_lint import check, load

with open("train.jsonl", encoding="utf-8") as handle:
    report = check(handle, require_object=True)

if not report.ok:
    for problem in report.problems:
        print(problem.line, problem.code, problem.message)
    print(report.codes())  # {'invalid-json': 2, 'blank': 1}

# Parse a file you have already checked.
with open("train.jsonl", encoding="utf-8") as handle:
    records = list(load(handle))
```

| Export | Purpose |
| --- | --- |
| `check(lines, *, require_object=False, check_duplicates=False)` | Returns a `Report` with `.problems`, `.records`, `.ok`, `.codes()`. |
| `iter_problems(lines, ...)` | Streams `Problem`s without building a report. |
| `load(lines)` | Yields parsed values, skipping blanks. Raises on the first bad line. |
| `Problem` | `line` (1-based), `code`, `message`. |

`check` and `iter_problems` accept any iterable of strings — a file object, a list, or a
generator — so they work on a stream you are already reading.

## Development

```sh
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT
