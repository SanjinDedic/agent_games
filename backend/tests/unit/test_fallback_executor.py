"""Unit tests for the fallback executor's run logic and process isolation.

run_exercise/run_snippet are called directly (in-process, no time limits) so
the test-runner process executes — and coverage measures — the run body; the
test script helper semantics (check/check_output/capture) live in
test_exercise_test_code.py. The *_isolated variants are exercised for real:
fresh forked child, armed soft timer, hard process-group kill — the tests
that prove the SIGALRM + SIGKILL design actually reaps spinners.
"""

import time

from backend.fallback_lambda.executor import (
    EXERCISE_TIMEOUT_MESSAGE,
    MAX_STDOUT_CHARS,
    SNIPPET_TIMEOUT_MESSAGE,
    run_exercise,
    run_exercise_isolated,
    run_snippet,
    run_snippet_isolated,
)

ADD_CODE = "def add(a, b):\n    return a + b"

ADD_TEST_CODE = (
    "def test_add():\n"
    '    """adds two numbers"""\n'
    "    check(add(1, 2), 3)\n"
)

EXERCISE_KEYS = {
    "status",
    "message",
    "passed",
    "test_results",
    "duration_ms",
    "traceback",
    "stdout",
}

SNIPPET_KEYS = {"status", "message", "stdout", "traceback", "duration_ms"}


def test_passing_submission():
    result = run_exercise(ADD_CODE, "add", ADD_TEST_CODE)
    assert result["status"] == "success"
    assert result["passed"] is True
    assert result["duration_ms"] is not None
    (case,) = result["test_results"]
    assert case["name"] == "adds two numbers"
    assert case["actual"] == "3"


def test_failing_expectation_is_success_not_error():
    test_code = (
        "def test_add():\n"
        "    check(add(1, 2), 4, name='custom name')\n"
    )
    result = run_exercise(ADD_CODE, "add", test_code)
    assert result["status"] == "success"
    assert result["passed"] is False
    assert result["test_results"][0]["name"] == "custom name"


def test_exception_inside_function_fails_that_test_only():
    result = run_exercise(
        "def add(a, b):\n    raise RuntimeError('boom')", "add", ADD_TEST_CODE
    )
    assert result["status"] == "success"
    assert result["passed"] is False
    assert result["test_results"][0]["error"] == "RuntimeError: boom"


def test_missing_entry_function():
    result = run_exercise("def other():\n    return 1", "add", ADD_TEST_CODE)
    assert result["status"] == "error"
    assert "must define a function named 'add'" in result["message"]


def test_code_that_crashes_before_tests():
    result = run_exercise("raise ValueError('bad module')", "add", ADD_TEST_CODE)
    assert result["status"] == "error"
    assert "failed to run before any tests started" in result["message"]
    assert "bad module" in result["traceback"]


def test_stdout_is_captured_and_bounded():
    result = run_exercise(
        f"print('x' * {MAX_STDOUT_CHARS * 2})\n{ADD_CODE}",
        "add",
        ADD_TEST_CODE,
    )
    assert result["status"] == "success"
    assert len(result["stdout"]) == MAX_STDOUT_CHARS


def test_execution_timeout_inside_function_maps_to_timeout_message():
    code = (
        "from backend.fallback_lambda.executor import ExecutionTimeout\n"
        "def add(a, b):\n"
        "    raise ExecutionTimeout()"
    )
    result = run_exercise(code, "add", ADD_TEST_CODE)
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE


def test_execution_timeout_during_exec_maps_to_timeout_message():
    code = (
        "from backend.fallback_lambda.executor import ExecutionTimeout\n"
        "raise ExecutionTimeout()"
    )
    result = run_exercise(code, "add", ADD_TEST_CODE)
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE


def test_exercise_without_test_code_is_an_authoring_error():
    result = run_exercise(ADD_CODE, "add", None)
    assert result["status"] == "error"
    assert "defines no tests" in result["message"]


# ---------------------------------------------------------------------------
# run_snippet: lesson demo blocks — exec + captured output, no entry
# function, no tests. Same direct-call rationale as run_exercise above.
# ---------------------------------------------------------------------------


def test_snippet_captures_stdout():
    result = run_snippet("print('hello')\nprint('world')")
    assert result["status"] == "success"
    assert result["stdout"] == "hello\nworld\n"
    assert result["traceback"] is None
    assert result["duration_ms"] is not None


def test_snippet_runs_as_main():
    result = run_snippet(
        "if __name__ == '__main__':\n    print('guarded')"
    )
    assert result["status"] == "success"
    assert result["stdout"] == "guarded\n"


def test_snippet_exception_returns_traceback_and_partial_stdout():
    result = run_snippet("print('before')\n1/0")
    assert result["status"] == "error"
    assert result["message"] == "ZeroDivisionError: division by zero"
    assert "ZeroDivisionError" in result["traceback"]
    assert result["stdout"] == "before\n"


def test_snippet_stdout_is_bounded():
    result = run_snippet(f"print('x' * {MAX_STDOUT_CHARS * 2})")
    assert result["status"] == "success"
    assert len(result["stdout"]) == MAX_STDOUT_CHARS


def test_snippet_execution_timeout_maps_to_timeout_message():
    code = (
        "from backend.fallback_lambda.executor import ExecutionTimeout\n"
        "raise ExecutionTimeout()"
    )
    result = run_snippet(code)
    assert result["status"] == "error"
    assert result["message"] == SNIPPET_TIMEOUT_MESSAGE


# ---------------------------------------------------------------------------
# Isolated variants: the real fork / soft timer / hard kill machinery.
# ---------------------------------------------------------------------------


def test_isolated_passing_submission_round_trips():
    result = run_exercise_isolated(ADD_CODE, "add", ADD_TEST_CODE)
    assert set(result) == EXERCISE_KEYS
    assert result["status"] == "success"
    assert result["passed"] is True
    assert result["test_results"][0]["actual"] == "3"


def test_isolated_spinner_is_killed_with_timeout_message():
    t0 = time.monotonic()
    result = run_exercise_isolated("while True:\n    pass", "add", ADD_TEST_CODE)
    elapsed = time.monotonic() - t0
    assert set(result) == EXERCISE_KEYS
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE
    assert elapsed < 4, f"hard kill took {elapsed:.1f}s"


def test_isolated_soft_limit_swallower_still_dies():
    # A bare `except Exception` swallows the soft ExecutionTimeout (exact
    # parity with Celery's soft limit); only the hard process-group SIGKILL
    # reaps it, mapping to the same timeout envelope.
    code = (
        "while True:\n"
        "    try:\n"
        "        while True:\n"
        "            pass\n"
        "    except Exception:\n"
        "        pass\n"
    )
    t0 = time.monotonic()
    result = run_exercise_isolated(code, "add", ADD_TEST_CODE)
    elapsed = time.monotonic() - t0
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE
    assert elapsed < 4, f"hard kill took {elapsed:.1f}s"


def test_isolated_snippet_spinner_gets_snippet_timeout_message():
    result = run_snippet_isolated("while True:\n    pass")
    assert set(result) == SNIPPET_KEYS
    assert result["status"] == "error"
    assert result["message"] == SNIPPET_TIMEOUT_MESSAGE


def test_isolated_snippet_success_round_trips():
    result = run_snippet_isolated("print('hello')")
    assert set(result) == SNIPPET_KEYS
    assert result["status"] == "success"
    assert result["stdout"] == "hello\n"
