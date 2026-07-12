"""Unit tests for the exercise task's in-process logic.

run_exercise is called directly (not via .delay) so the test-runner process
executes — and coverage measures — the task body; the enqueue-to-worker path
is exercised end-to-end by the tutorial router integration tests.
"""

from unittest.mock import MagicMock

import pytest

from backend.tasks.exercise_task import (
    EXERCISE_TIMEOUT_MESSAGE,
    MAX_STDOUT_CHARS,
    await_exercise_result,
    run_exercise,
    timeout_exercise_result,
)

ADD_CASES = [{"args": [1, 2], "expected": 3}]


def test_passing_submission():
    result = run_exercise("def add(a, b):\n    return a + b", "add", ADD_CASES)
    assert result["status"] == "success"
    assert result["passed"] is True
    assert result["duration_ms"] is not None
    (case,) = result["test_results"]
    assert case["call"] == "add(1, 2)"
    assert case["actual"] == "3"


def test_failing_expectation_is_success_not_error():
    result = run_exercise(
        "def add(a, b):\n    return a + b",
        "add",
        [{"args": [1, 2], "expected": 4, "name": "custom name"}],
    )
    assert result["status"] == "success"
    assert result["passed"] is False
    assert result["test_results"][0]["name"] == "custom name"


def test_exception_inside_function_fails_that_test_only():
    result = run_exercise(
        "def add(a, b):\n    raise RuntimeError('boom')", "add", ADD_CASES
    )
    assert result["status"] == "success"
    assert result["passed"] is False
    assert result["test_results"][0]["error"] == "RuntimeError: boom"


def test_mutating_function_cannot_corrupt_the_reported_call():
    result = run_exercise(
        "def total(xs):\n    xs.append(1)\n    return sum(xs)",
        "total",
        [{"args": [[1, 2]], "expected": 4}],
    )
    assert result["passed"] is True
    assert result["test_results"][0]["call"] == "total([1, 2])"


def test_missing_entry_function():
    result = run_exercise("def other():\n    return 1", "add", ADD_CASES)
    assert result["status"] == "error"
    assert "must define a function named 'add'" in result["message"]


def test_code_that_crashes_before_tests():
    result = run_exercise("raise ValueError('bad module')", "add", ADD_CASES)
    assert result["status"] == "error"
    assert "failed to run before any tests started" in result["message"]
    assert "bad module" in result["traceback"]


def test_stdout_is_captured_and_bounded():
    result = run_exercise(
        f"print('x' * {MAX_STDOUT_CHARS * 2})\ndef add(a, b):\n    return a + b",
        "add",
        ADD_CASES,
    )
    assert result["status"] == "success"
    assert len(result["stdout"]) == MAX_STDOUT_CHARS


def test_soft_time_limit_inside_function_maps_to_timeout_message():
    code = (
        "from celery.exceptions import SoftTimeLimitExceeded\n"
        "def add(a, b):\n"
        "    raise SoftTimeLimitExceeded()"
    )
    result = run_exercise(code, "add", ADD_CASES)
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE


def test_soft_time_limit_during_exec_maps_to_timeout_message():
    code = (
        "from celery.exceptions import SoftTimeLimitExceeded\n"
        "raise SoftTimeLimitExceeded()"
    )
    result = run_exercise(code, "add", ADD_CASES)
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE


def test_malformed_test_cases_hit_the_task_boundary_catch_all():
    result = run_exercise("def add(a, b):\n    return a + b", "add", None)
    assert result["status"] == "error"
    assert "Error while running tests" in result["message"]
    assert result["traceback"] is not None


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
