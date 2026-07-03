"""Async, concurrency-safe retrieval of Celery task results.

Blocking ``AsyncResult.get()`` drives Celery's Redis result backend through a
single shared, non-thread-safe pubsub *result consumer*. Calling it concurrently
from many request handlers (previously via ``asyncio.to_thread``) desynced that
consumer's socket under load and left it permanently raising ``Protocol Error``
until the API process restarted — the "Celery never recovers" wedge seen when a
submission flood hit the validator.

``poll_task_result`` avoids the consumer entirely: it polls
``AsyncResult.ready()`` — a plain result-backend GET served from the connection
pool, safe under concurrency — and yields to the event loop between checks, so
there is no worker thread and no shared pubsub socket to corrupt. A task that
outlives the caller's deadline is revoked WITHOUT terminate: a still-queued
task is discarded when the worker receives it, and a running one is killed by
its own hard time_limit. Never revoke(terminate=True) here — SIGKILLing pool
children races billiard's fork-per-task recycling (worker_max_tasks_per_child=1)
and leaks unreaped zombies until the container's pids_limit is exhausted, after
which every fork fails EAGAIN and the pool is permanently wedged (reproduced
under submission-flood load; recovery required a container restart).
"""

import asyncio
import time

from celery.result import AsyncResult


async def poll_task_result(
    async_result: AsyncResult,
    timeout: float,
    interval: float = 0.1,
):
    """Await a Celery task result without blocking the loop or the pubsub consumer.

    Returns the task's return value on success. Re-raises the task's stored
    exception on failure (matching ``.get(propagate=True)``). Raises
    ``TimeoutError`` — and revokes the task — if it does not finish within
    ``timeout`` seconds. The revoke only discards the task if it is still
    queued; a running task is left to its hard time_limit, which is the sole
    kill mechanism (see module docstring for why terminate=True is forbidden).
    """
    deadline = time.monotonic() + timeout
    while not async_result.ready():
        if time.monotonic() >= deadline:
            async_result.revoke()
            raise TimeoutError(
                f"task {async_result.id} did not finish within {timeout}s"
            )
        await asyncio.sleep(interval)

    # ready() cached the terminal meta, so state/result read locally (no re-GET).
    if async_result.successful():
        return async_result.result
    exc = async_result.result
    if isinstance(exc, BaseException):
        raise exc
    raise RuntimeError(str(exc) if exc is not None else async_result.state)
