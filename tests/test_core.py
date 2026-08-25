import json

import pytest

from jsonl_lint.core import BOM, check, iter_problems, load


def codes(lines, **kwargs):
    return [problem.code for problem in iter_problems(lines, **kwargs)]


def test_clean_file_has_no_problems():
    report = check(['{"a": 1}', '{"a": 2}'])
    assert report.ok
    assert report.records == 2


def test_every_bad_line_is_reported_not_just_the_first():
    report = check(["nope", "also nope", '{"a": 1}', "{"])
    assert [problem.line for problem in report.problems] == [1, 2, 4]


def test_line_numbers_are_one_based():
    (problem,) = list(iter_problems(["oops"]))
    assert problem.line == 1


def test_blank_lines_are_flagged_and_not_double_reported():
    assert codes(["", "   ", "\t"]) == ["blank", "blank", "blank"]


def test_blank_lines_do_not_count_as_records():
    report = check(['{"a": 1}', "", "   "])
    assert report.records == 1


def test_bom_on_the_first_line_is_reported_once():
    assert codes([BOM + '{"a": 1}', '{"a": 2}']) == ["bom"]


def test_bom_does_not_also_cause_a_parse_error():
    # The BOM is stripped before parsing, so the line is otherwise valid.
    assert "invalid-json" not in codes([BOM + '{"a": 1}'])


def test_a_bom_further_down_the_file_is_a_parse_error_not_a_bom_warning():
    # Only the first line can legitimately carry one.
    assert codes(['{"a": 1}', BOM + '{"a": 2}']) == ["invalid-json"]


def test_surrounding_whitespace_is_reported_but_still_parses():
    assert codes(['  {"a": 1}  ']) == ["whitespace"]


def test_trailing_newlines_are_not_whitespace_problems():
    assert codes(['{"a": 1}\n', '{"a": 2}\r\n']) == []


def test_require_object_rejects_non_objects():
    assert codes(["[1, 2]", "42", '"text"', "null"], require_object=True) == ["not-an-object"] * 4


def test_require_object_is_off_by_default():
    assert codes(["[1, 2]", "42"]) == []


def test_require_object_names_the_type_it_found():
    (problem,) = list(iter_problems(["[1, 2]"], require_object=True))
    assert "list" in problem.message


def test_problem_str_is_readable():
    (problem,) = list(iter_problems(["oops"]))
    assert str(problem).startswith("line 1: invalid-json:")


def test_codes_counts_each_kind():
    report = check(["bad", "worse", ""])
    assert report.codes() == {"invalid-json": 2, "blank": 1}


def test_report_of_a_clean_file_summarises_nothing():
    assert check(['{"a": 1}']).codes() == {}


def test_load_yields_parsed_values_and_skips_blanks():
    assert list(load(['{"a": 1}', "", "[2]"])) == [{"a": 1}, [2]]


def test_load_raises_on_the_first_bad_line():
    with pytest.raises(json.JSONDecodeError):
        list(load(['{"a": 1}', "nope"]))


def test_check_accepts_a_generator():
    report = check(line for line in ['{"a": 1}', "nope"])
    assert report.records == 2
    assert len(report.problems) == 1
