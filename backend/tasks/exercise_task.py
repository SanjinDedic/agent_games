"""The Celery exercise-run task and its enqueue/await helpers.

Mirrors backend/tasks/validation_task.py: the AST safety check runs in the API
process before enqueue (backend/routes/user/code_validation.py), so unsafe code
never reaches a worker. The task executes the student's code inside a worker
child process; worker_max_tasks_per_child=1 gives every task a fresh process,
so submitted code cannot contaminate later runs.

An exercise's tests are an admin-trusted Python test script
(backend/tasks/exercise_test_code.py) exec'd into the same namespace as the
student's code. A failing check is a normal outcome ("status": "success",
test not passed) — "status": "error" means the code never got as far as
producing test results (syntax error, missing function, timeout).
"""

import contextlib
import io
import time
import traceback as tb
from typing import Any, Dict, Optional

from billiard.exceptions import WorkerLostError
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded

from backend.tasks.celery_app import celery_app
from backend.tasks.celery_utils import poll_task_result
from backend.tasks.exercise_test_code import MAX_STDOUT_CHARS, run_test_code
from backend.tasks.validation_task import (
    VALIDATION_RESULT_TIMEOUT,
    VALIDATION_TASK_EXPIRES,
)

# An exercise run is a handful of pure-function calls — far lighter than a
# validation (no game, no simulations) — so it gets a much tighter budget.
# Plain constants, not env-overridable like VALIDATION_TIMEOUT_SECONDS: nothing
# needs to shorten 1s further for tests, and a constant cannot drift between
# the enqueuing process (which stamps limits into each task message, overriding
# worker-side defaults) and the workers.
EXERCISE_TIMEOUT_SECONDS = 1

# Hard SIGKILL backstop, 1s past the soft limit — same rationale as
# VALIDATION_TIME_LIMIT: student code with a bare `except Exception` swallows
# SoftTimeLimitExceeded, and only the hard kill reliably reaps a spinner.
EXERCISE_TIME_LIMIT = EXERCISE_TIMEOUT_SECONDS + 1

_plural = "" if EXERCISE_TIMEOUT_SECONDS == 1 else "s"
EXERCISE_TIMEOUT_MESSAGE = (
    f"Your code consumes too much time - the tests did not finish within "
    f"{EXERCISE_TIMEOUT_SECONDS} second{_plural}. It may be stuck in a loop."
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


def enqueue_exercise_run(
    code: str, entry_function: str, test_code: Optional[str]
):
    """Enqueue an exercise run that self-drops if it waits out its usefulness.

    Same expiry rationale as enqueue_validation: a task still queued after the
    submitter has given up is discarded instead of run.
    """
    return run_exercise.apply_async(
        kwargs={
            "code": code,
            "entry_function": entry_function,
            "test_code": test_code,
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


def _execute_tests(
    code: str, entry_function: str, test_code: Optional[str]
) -> Dict[str, Any]:
    """Exec the student's code, run the test script, return the raw result."""
    t0 = time.perf_counter()
    namespace: Dict[str, Any] = {"__name__": "exercise_submission"}
    try:
        exec(code, namespace)  # noqa: S102 - AST-checked, isolated worker
    except SoftTimeLimitExceeded:
        raise
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

    test_results: list = []
    if test_code:
        error = run_test_code(test_code, namespace, test_results)
        if error:
            return error

    if not test_results:
        # A missing/row-less test script would otherwise pass vacuously; this
        # is an authoring bug, not a student failure — surface it loudly.
        return {
            "status": "error",
            "message": "This exercise defines no tests.",
        }

    return {
        "status": "success",
        "passed": all(t["passed"] for t in test_results),
        "test_results": test_results,
        "duration_ms": (time.perf_counter() - t0) * 1000,
    }


@celery_app.task(
    name="validation.run_exercise",
    soft_time_limit=EXERCISE_TIMEOUT_SECONDS,
    time_limit=EXERCISE_TIME_LIMIT,
)
def run_exercise(
    code: str, entry_function: str, test_code: Optional[str]
) -> Dict[str, Any]:
    """Execute the student's code and run the exercise's test script on it."""
    buf = io.StringIO()
    result: Dict[str, Any]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            result = _execute_tests(code, entry_function, test_code)
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
