"""Unit tests for poll_task_result's timeout contract.

The one behavior that must never regress: on caller timeout the task is
revoked WITHOUT terminate. revoke(terminate=True, signal="SIGKILL") races
billiard's fork-per-task recycling (worker_max_tasks_per_child=1) and leaks
unreaped zombie children until the worker container's pids_limit is exhausted,
permanently wedging the pool (every fork fails EAGAIN; only a container
restart recovers). Running tasks are killed by their own hard time_limit —
that is the sole kill mechanism.
"""

from unittest.mock import MagicMock

import pytest

from backend.celery_utils import poll_task_result


@pytest.mark.asyncio
async def test_timeout_revokes_without_terminate():
    async_result = MagicMock()
    async_result.ready.return_value = False
    async_result.id = "test-task-id"

    with pytest.raises(TimeoutError):
        await poll_task_result(async_result, timeout=0.05, interval=0.01)

    async_result.revoke.assert_called_once_with()
    _, kwargs = async_result.revoke.call_args
    assert "terminate" not in kwargs, (
        "revoke(terminate=...) SIGKILLs pool children and leaks zombies until "
        "pids_limit wedges the worker — running tasks must be left to their "
        "hard time_limit"
    )


@pytest.mark.asyncio
async def test_success_returns_result_without_revoke():
    async_result = MagicMock()
    async_result.ready.return_value = True
    async_result.successful.return_value = True
    async_result.result = {"status": "success"}

    result = await poll_task_result(async_result, timeout=1)

    assert result == {"status": "success"}
    async_result.revoke.assert_not_called()


@pytest.mark.asyncio
async def test_failure_reraises_stored_exception():
    async_result = MagicMock()
    async_result.ready.return_value = True
    async_result.successful.return_value = False
    async_result.result = ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await poll_task_result(async_result, timeout=1)
