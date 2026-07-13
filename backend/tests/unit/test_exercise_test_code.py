"""Unit tests for the exercise test-script runner (exercise_test_code.py).

Everything goes through run_exercise so the rows tested here are exactly the
rows the API returns and the frontend renders.
"""

import json

from backend.tasks.exercise_task import (
    EXERCISE_TIMEOUT_MESSAGE,
    run_exercise,
)
from backend.tasks.exercise_test_code import MAX_STDOUT_CHARS

ADD_CODE = "def add(a, b):\n    return a + b"

ROW_KEYS = {"name", "call", "expected", "actual", "passed", "error"}


def test_check_rows_have_the_full_row_shape():
    test_code = (
        "def test_math():\n"
        "    check(add(1, 2), 3, name='one plus two')\n"
        "    check(add(2, 2), 5, name='two plus two, wrong')\n"
    )
    result = run_exercise(ADD_CODE, "add", test_code)
    assert result["status"] == "success"
    assert result["passed"] is False
    passing, failing = result["test_results"]
    assert set(passing) == ROW_KEYS and set(failing) == ROW_KEYS
    assert passing == {
        "name": "one plus two",
        "call": None,
        "expected": 3,
        "actual": "3",
        "passed": True,
        "error": None,
    }
    # check() must not raise on failure: the second row exists and records
    # the mismatch.
    assert failing["passed"] is False
    assert failing["expected"] == 5
    assert failing["actual"] == "4"


def test_unnamed_check_row_is_named_from_the_docstring():
    test_code = (
        "def test_add():\n"
        '    """adds small numbers"""\n'
        "    check(add(1, 2), 3)\n"
    )
    result = run_exercise(ADD_CODE, "add", test_code)
    assert result["test_results"][0]["name"] == "adds small numbers"


def test_check_output_tolerates_trailing_whitespace_and_newline():
    test_code = (
        "def test_out():\n"
        "    check_output('Alice: 30  \\nBob: 55\\n', 'Alice: 30\\nBob: 55')\n"
    )
    result = run_exercise(ADD_CODE, "add", test_code)
    assert result["passed"] is True


def test_check_output_mismatch_records_raw_text():
    test_code = (
        "def test_out():\n"
        "    check_output('Alice: 99\\n', 'Alice: 30\\nBob: 55', name='board')\n"
    )
    result = run_exercise(ADD_CODE, "add", test_code)
    assert result["passed"] is False
    (row,) = result["test_results"]
    # Raw text, not repr — the UI shows real newlines.
    assert row["expected"] == "Alice: 30\nBob: 55"
    assert row["actual"] == "Alice: 99\n"


def test_capture_truncates_at_max_stdout_chars():
    test_code = (
        "def test_big():\n"
        "    with capture() as out:\n"
        f"        print('x' * {MAX_STDOUT_CHARS * 2})\n"
        f"    check(len(out.text), {MAX_STDOUT_CHARS})\n"
    )
    result = run_exercise(ADD_CODE, "add", test_code)
    assert result["passed"] is True


def test_captured_output_stays_out_of_the_stdout_panel():
    test_code = (
        "def test_quiet():\n"
        "    with capture() as out:\n"
        "        print('hidden from the panel')\n"
        "    check_output(out.text, 'hidden from the panel')\n"
    )
    result = run_exercise(ADD_CODE, "add", test_code)
    assert result["passed"] is True
    assert result["stdout"] is None


def test_uncaught_exception_becomes_error_row_named_from_docstring():
    test_code = (
        "def test_boom():\n"
        '    """explodes helpfully"""\n'
        "    raise ValueError('bad')\n"
    )
    result = run_exercise(ADD_CODE, "add", test_code)
    assert result["status"] == "success"
    assert result["passed"] is False
    (row,) = result["test_results"]
    assert row["name"] == "explodes helpfully"
    assert row["error"] == "ValueError: bad"


def test_bare_failing_assert_falls_back_to_function_name():
    test_code = "def test_assertion():\n    assert add(1, 1) == 3\n"
    result = run_exercise(ADD_CODE, "add", test_code)
    (row,) = result["test_results"]
    assert row["name"] == "test_assertion"
    assert row["error"] == "AssertionError"
    assert row["passed"] is False


def test_student_defined_test_functions_are_not_collected():
    student = (
        f"{ADD_CODE}\n"
        "def test_sneaky():\n"
        "    raise RuntimeError('student test ran')\n"
    )
    test_code = "def test_real():\n    check(add(1, 2), 3)\n"
    result = run_exercise(student, "add", test_code)
    assert result["passed"] is True
    assert len(result["test_results"]) == 1


def test_student_predefined_name_cannot_shadow_a_script_test():
    """A student defining test_real themselves must not suppress the script's
    test_real (redefined names are still collected)."""
    student = f"{ADD_CODE}\ndef test_real():\n    pass\n"
    test_code = "def test_real():\n    check(add(2, 2), 5)\n"
    result = run_exercise(student, "add", test_code)
    assert result["passed"] is False
    assert len(result["test_results"]) == 1


def test_soft_time_limit_inside_a_test_function_propagates():
    test_code = (
        "from celery.exceptions import SoftTimeLimitExceeded\n"
        "def test_spin():\n"
        "    raise SoftTimeLimitExceeded()\n"
    )
    result = run_exercise(ADD_CODE, "add", test_code)
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE


def test_tuple_expected_is_sanitized_and_result_serializes():
    student = "def make():\n    return (2, 3)"
    test_code = "def test_pair():\n    check(make(), (2, 3))\n"
    result = run_exercise(student, "make", test_code)
    assert result["passed"] is True
    (row,) = result["test_results"]
    # Recorded in wire format: same row in-process as through the broker
    assert row["expected"] == [2, 3]
    json.dumps(result)  # the whole payload must survive the result backend


def test_unserializable_expected_falls_back_to_repr():
    student = "def make():\n    return {2, 3}"
    test_code = "def test_set():\n    check(make(), {2, 3})\n"
    result = run_exercise(student, "make", test_code)
    assert result["passed"] is True  # compared before sanitizing
    (row,) = result["test_results"]
    assert row["expected"] == repr({2, 3})
    json.dumps(result)


def test_script_exec_error_is_an_authoring_error():
    result = run_exercise(ADD_CODE, "add", "this is not python")
    assert result["status"] == "error"
    assert "test script failed to run" in result["message"]
    assert result["traceback"] is not None


def test_rowless_script_hits_the_no_tests_guard():
    result = run_exercise(ADD_CODE, "add", "def test_nothing():\n    pass\n")
    assert result["status"] == "error"
    assert "defines no tests" in result["message"]


def test_check_output_accepts_the_capture_object_itself():
    student = "def greet():\n    print('hi')"
    test_code = (
        "def test_greet():\n"
        "    with capture() as out:\n"
        "        greet()\n"
        "    check_output(out, 'hi')\n"
    )
    result = run_exercise(student, "greet", test_code)
    assert result["passed"] is True
