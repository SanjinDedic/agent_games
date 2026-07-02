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
outlives the caller's deadline is revoked and SIGKILLed so an abandoned or
runaway agent stops holding a worker core.
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
    ``TimeoutError`` — and revokes + SIGKILLs the task — if it does not finish
    within ``timeout`` seconds, so a backlogged or spinning task the caller has
    given up on cannot keep burning a worker core.
    """
    deadline = time.monotonic() + timeout
    while not async_result.ready():
        if time.monotonic() >= deadline:
            async_result.revoke(terminate=True, signal="SIGKILL")
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
