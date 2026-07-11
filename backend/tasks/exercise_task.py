"""The Celery exercise-run task and its enqueue/await helpers.

Mirrors backend/tasks/validation_task.py: the AST safety check runs in the API
process before enqueue (backend/routes/user/code_validation.py), so unsafe code
never reaches a worker. The task executes the student's code inside a worker
child process; worker_max_tasks_per_child=1 gives every task a fresh process,
so submitted code cannot contaminate later runs.

Exercises are function I/O tests: the student's code must define the exercise's
entry function, and each test case calls it with `args` and compares the return
value to `expected` with ==. A failing test is a normal outcome ("status":
"success", test not passed) — "status": "error" means the code never got as far
as producing test results (syntax error, missing function, timeout).
"""

import contextlib
import copy
import io
import time
import traceback as tb
from typing import Any, Dict, List

from billiard.exceptions import WorkerLostError
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded

from backend.tasks.celery_app import celery_app
from backend.tasks.celery_utils import poll_task_result
from backend.tasks.validation_task import (
    VALIDATION_RESULT_TIMEOUT,
    VALIDATION_TASK_EXPIRES,
    VALIDATION_TIME_LIMIT,
    VALIDATION_TIMEOUT_SECONDS,
)

# Students print-debug; keep captured output bounded so a print inside a loop
# can't bloat the result payload through the broker.
MAX_STDOUT_CHARS = 10_000

EXERCISE_TIMEOUT_MESSAGE = (
    f"Your code consumes too much time - the tests did not finish within "
    f"{VALIDATION_TIMEOUT_SECONDS} seconds. It may be stuck in a loop."
)


def _normalize(result: Dict[str, Any]) -> Dict[str, Any]:
    """Return the full ExerciseRunResponse shape consumers expect."""
    return {
        "status": result.get("status", "error"),
        "message": result.get("message"),
        "passed": result.get("passed", False),
        "test_results": result.get("test_results", []),
        "duration_ms": result.get("duration_ms"),
        "traceback": result.get("traceback"),
        "stdout": result.get("stdout"),
    }


def timeout_exercise_result() -> Dict[str, Any]:
    """ExerciseRunResponse dict for a hard-killed (timed-out) exercise task."""
    return _normalize({"status": "error", "message": EXERCISE_TIMEOUT_MESSAGE})


def enqueue_exercise_run(code: str, entry_function: str, test_cases: List[dict]):
    """Enqueue an exercise run that self-drops if it waits out its usefulness.

    Same expiry rationale as enqueue_validation: a task still queued after the
    submitter has given up is discarded instead of run.
    """
    return run_exercise.apply_async(
        kwargs={
            "code": code,
            "entry_function": entry_function,
            "test_cases": test_cases,
        },
        expires=VALIDATION_TASK_EXPIRES,
    )


async def await_exercise_result(
    async_result, timeout: float = VALIDATION_RESULT_TIMEOUT
) -> Dict[str, Any]:
    """Await an exercise task and always return a normalized ExerciseRunResponse.

    A worker killed by the hard time limit or OOM, and a task that outlives the
    caller's patience, all map to the same user-facing timeout failure.
    """
    try:
        return await poll_task_result(async_result, timeout)
    except (TimeLimitExceeded, WorkerLostError, TimeoutError):
        return timeout_exercise_result()
    except Exception as e:  # noqa: BLE001 - any task fault becomes a clean error
        return _normalize(
            {"status": "error", "message": f"Error while running tests: {e}"}
        )


def _format_call(entry_function: str, args: List[Any]) -> str:
    return f"{entry_function}({', '.join(repr(a) for a in args)})"


def _execute_tests(
    code: str, entry_function: str, test_cases: List[dict]
) -> Dict[str, Any]:
    """Exec the student's code, run every test case, return the raw result."""
    t0 = time.perf_counter()
    namespace: Dict[str, Any] = {"__name__": "exercise_submission"}
    try:
        exec(code, namespace)  # noqa: S102 - AST-checked, isolated worker
    except Exception:
        return {
            "status": "error",
            "message": "Your code failed to run before any tests started.",
            "traceback": tb.format_exc(),
        }

    func = namespace.get(entry_function)
    if not callable(func):
        return {
            "status": "error",
            "message": f"Your code must define a function named '{entry_function}'.",
        }

    test_results = []
    for case in test_cases:
        # deepcopy so a function that mutates its arguments can't leak state
        # into (or corrupt) later test cases
        args = copy.deepcopy(case.get("args", []))
        expected = case.get("expected")
        entry = {
            "name": case.get("name") or _format_call(entry_function, args),
            "call": _format_call(entry_function, case.get("args", [])),
            "expected": expected,
            "actual": None,
            "passed": False,
            "error": None,
        }
        try:
            actual = func(*args)
            entry["actual"] = repr(actual)
            entry["passed"] = bool(actual == expected)
        except Exception as e:  # noqa: BLE001 - a crash fails this test only
            entry["error"] = f"{type(e).__name__}: {e}"
        test_results.append(entry)

    return {
        "status": "success",
        "passed": all(t["passed"] for t in test_results),
        "test_results": test_results,
        "duration_ms": (time.perf_counter() - t0) * 1000,
    }


@celery_app.task(
    name="validation.run_exercise",
    soft_time_limit=VALIDATION_TIMEOUT_SECONDS,
    time_limit=VALIDATION_TIME_LIMIT,
)
def run_exercise(
    code: str, entry_function: str, test_cases: List[dict]
) -> Dict[str, Any]:
    """Execute the student's code and run every test case against it."""
    buf = io.StringIO()
    result: Dict[str, Any]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            result = _execute_tests(code, entry_function, test_cases)
    except SoftTimeLimitExceeded:
        # Only reached when the student's code didn't swallow it; a bare
        # `except Exception` in their code spins on until the hard time_limit
        # SIGKILL, which the router maps to the same message.
        result = {
            "status": "error",
            "message": EXERCISE_TIMEOUT_MESSAGE,
        }
    except Exception as e:  # noqa: BLE001 - the task boundary is the catch-all
        result = {
            "status": "error",
            "message": f"Error while running tests: {str(e)}",
            "traceback": tb.format_exc(),
        }
    captured = buf.getvalue()
    if captured.strip():
        result["stdout"] = captured[:MAX_STDOUT_CHARS]
    return _normalize(result)
