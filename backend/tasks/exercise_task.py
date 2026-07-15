"""API-side enqueue/await helpers for the exercises queue.

The task itself (``exercises.run``) lives in backend/exercise_worker/tasks.py
and runs on the dedicated slim worker-exercises container — see that module
for the execution model (zero code validation, 0.5s soft / 1.5s hard time
limit, fresh process per task). This module never registers the task: it
enqueues by name via ``send_task`` (routed to the ``exercises`` queue by
celery_app's task_routes), so the API process stays decoupled from the
worker's own Celery app.
"""

from typing import Any, Dict, Optional

from billiard.exceptions import WorkerLostError
from celery.exceptions import TimeLimitExceeded

from backend.exercise_worker.tasks import (
    EXERCISE_TIMEOUT_MESSAGE,
    normalize_result,
)
from backend.tasks.celery_app import celery_app
from backend.tasks.celery_utils import poll_task_result

# How long the API waits on a result before giving up. Covers the 1.5s hard
# time limit plus queue wait on the two-slot worker under a submission burst.
EXERCISE_RESULT_TIMEOUT = 6

# A task still queued after this many seconds is discarded instead of run —
# the submitter's request has already timed out, so running it helps nobody.
EXERCISE_TASK_EXPIRES = 8


def timeout_exercise_result() -> Dict[str, Any]:
    """ExerciseRunResponse dict for a hard-killed (timed-out) exercise task."""
    return normalize_result(
        {"status": "error", "message": EXERCISE_TIMEOUT_MESSAGE}
    )


def enqueue_exercise_run(
    code: str, entry_function: str, test_code: Optional[str]
):
    """Enqueue an exercise run that self-drops if it waits out its usefulness."""
    return celery_app.send_task(
        "exercises.run",
        kwargs={
            "code": code,
            "entry_function": entry_function,
            "test_code": test_code,
        },
        expires=EXERCISE_TASK_EXPIRES,
    )


async def await_exercise_result(
    async_result, timeout: float = EXERCISE_RESULT_TIMEOUT
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
        return normalize_result(
            {"status": "error", "message": f"Error while running tests: {e}"}
        )
