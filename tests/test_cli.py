import re

import pytest

from jsonl_lint.cli import EXIT_OK, EXIT_PROBLEMS, main


def _problem_lines(out):
    # The trailing summary line repeats every code, so count the rendered
    # problem lines by their "line N:" prefix instead of counting code names.
    return [line for line in out.splitlines() if re.search(r":line \d+:", line)]


@pytest.fixture
def jsonl(tmp_path):
    def write(name, text):
        path = tmp_path / name
        # newline="" so CRLF written by a test is not translated again
        # into CR CRLF by Windows text-mode writing.
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        return str(path)

    return write


def test_clean_file_exits_zero(jsonl, capsys):
    path = jsonl("good.jsonl", '{"a": 1}\n{"a": 2}\n')
    assert main([path]) == EXIT_OK
    assert "0 problems" in capsys.readouterr().out


def test_bad_file_exits_one(jsonl, capsys):
    path = jsonl("bad.jsonl", '{"a": 1}\nnope\n')
    assert main([path]) == EXIT_PROBLEMS
    assert "invalid-json" in capsys.readouterr().out


def test_quiet_prints_nothing_but_keeps_the_exit_code(jsonl, capsys):
    path = jsonl("bad.jsonl", "nope\n")
    assert main([path, "--quiet"]) == EXIT_PROBLEMS
    assert capsys.readouterr().out == ""


def test_require_object_flag_is_passed_through(jsonl):
    path = jsonl("array.jsonl", "[1, 2]\n")
    assert main([path]) == EXIT_OK
    assert main([path, "--require-object"]) == EXIT_PROBLEMS


def test_max_problems_truncates_and_says_so(jsonl, capsys):
    path = jsonl("bad.jsonl", "a\nb\nc\nd\n")
    main([path, "--max-problems", "2"])
    out = capsys.readouterr().out
    assert len(_problem_lines(out)) == 2
    assert "and 2 more" in out


def test_max_problems_zero_shows_everything(jsonl, capsys):
    path = jsonl("bad.jsonl", "a\nb\nc\n")
    main([path, "--max-problems", "0"])
    assert len(_problem_lines(capsys.readouterr().out)) == 3


def test_several_files_are_all_checked_and_labelled(jsonl, capsys):
    good = jsonl("good.jsonl", '{"a": 1}\n')
    bad = jsonl("bad.jsonl", "nope\n")
    assert main([good, bad]) == EXIT_PROBLEMS
    out = capsys.readouterr().out
    assert "good.jsonl" in out and "bad.jsonl" in out


def test_one_bad_file_fails_the_whole_run(jsonl):
    good = jsonl("good.jsonl", '{"a": 1}\n')
    bad = jsonl("bad.jsonl", "nope\n")
    assert main([good, bad]) == EXIT_PROBLEMS


def test_missing_file_reports_and_fails(capsys):
    assert main(["does-not-exist.jsonl"]) == EXIT_PROBLEMS
    assert "does-not-exist.jsonl" in capsys.readouterr().err


def test_a_missing_file_does_not_stop_later_files(jsonl, capsys):
    good = jsonl("good.jsonl", '{"a": 1}\n')
    main(["missing.jsonl", good])
    assert "good.jsonl" in capsys.readouterr().out


def test_stdin_is_read_when_no_path_is_given(monkeypatch, capsys):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO('{"a": 1}\nnope\n'))
    assert main([]) == EXIT_PROBLEMS
    assert "<stdin>" in capsys.readouterr().out


def test_crlf_file_is_not_reported_as_whitespace(jsonl, capsys):
    path = jsonl("crlf.jsonl", '{"a": 1}\r\n{"a": 2}\r\n')
    assert main([path]) == EXIT_OK
