"""Unit tests for the exercise task's in-process logic.

run_exercise is called directly (not via .delay) so the test-runner process
executes — and coverage measures — the task body; the enqueue-to-worker path
is exercised end-to-end by the tutorial router integration tests. The test
script helper semantics (check/check_output/capture) live in
test_exercise_test_code.py; this file covers the task-level plumbing around
them.
"""

from unittest.mock import MagicMock

import pytest

from backend.exercise_worker.tasks import (
    EXERCISE_TIMEOUT_MESSAGE,
    MAX_STDOUT_CHARS,
    run_exercise,
)
from backend.tasks.exercise_task import (
    await_exercise_result,
    timeout_exercise_result,
)

ADD_CODE = "def add(a, b):\n    return a + b"

ADD_TEST_CODE = (
    "def test_add():\n"
    '    """adds two numbers"""\n'
    "    check(add(1, 2), 3)\n"
)


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


def test_soft_time_limit_inside_function_maps_to_timeout_message():
    code = (
        "from celery.exceptions import SoftTimeLimitExceeded\n"
        "def add(a, b):\n"
        "    raise SoftTimeLimitExceeded()"
    )
    result = run_exercise(code, "add", ADD_TEST_CODE)
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE


def test_soft_time_limit_during_exec_maps_to_timeout_message():
    code = (
        "from celery.exceptions import SoftTimeLimitExceeded\n"
        "raise SoftTimeLimitExceeded()"
    )
    result = run_exercise(code, "add", ADD_TEST_CODE)
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE


def test_exercise_without_test_code_is_an_authoring_error():
    result = run_exercise(ADD_CODE, "add", None)
    assert result["status"] == "error"
    assert "defines no tests" in result["message"]


def test_timeout_exercise_result_shape():
    result = timeout_exercise_result()
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE
    assert result["passed"] is False
    assert result["test_results"] == []


@pytest.mark.asyncio
async def test_await_returns_task_result():
    async_result = MagicMock()
    async_result.ready.return_value = True
    async_result.successful.return_value = True
    async_result.result = {"status": "success", "passed": True}

    result = await await_exercise_result(async_result, timeout=1)
    assert result == {"status": "success", "passed": True}


@pytest.mark.asyncio
async def test_await_timeout_maps_to_timeout_result():
    async_result = MagicMock()
    async_result.ready.return_value = False
    async_result.id = "test-task-id"

    result = await await_exercise_result(async_result, timeout=0.05)
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE


@pytest.mark.asyncio
async def test_await_task_fault_becomes_clean_error():
    async_result = MagicMock()
    async_result.ready.side_effect = RuntimeError("worker fault")

    result = await await_exercise_result(async_result, timeout=1)
    assert result["status"] == "error"
    assert "Error while running tests" in result["message"]


# ---------------------------------------------------------------------------
# run_snippet: lesson demo blocks — exec + captured output, no entry
# function, no tests. Same direct-call rationale as run_exercise above.
# ---------------------------------------------------------------------------

from backend.exercise_worker.tasks import (  # noqa: E402
    SNIPPET_TIMEOUT_MESSAGE,
    run_snippet,
)
from backend.tasks.exercise_task import await_snippet_result  # noqa: E402


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


def test_snippet_soft_time_limit_maps_to_timeout_message():
    code = (
        "from celery.exceptions import SoftTimeLimitExceeded\n"
        "raise SoftTimeLimitExceeded()"
    )
    result = run_snippet(code)
    assert result["status"] == "error"
    assert result["message"] == SNIPPET_TIMEOUT_MESSAGE


@pytest.mark.asyncio
async def test_await_snippet_timeout_maps_to_timeout_result():
    async_result = MagicMock()
    async_result.ready.return_value = False
    async_result.id = "test-task-id"

    result = await await_snippet_result(async_result, timeout=0.05)
    assert result["status"] == "error"
    assert result["message"] == SNIPPET_TIMEOUT_MESSAGE
