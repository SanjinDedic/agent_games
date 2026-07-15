import gc
import os

from celery import Celery
from celery.concurrency.asynpool import AsynPool
from celery.signals import worker_process_init, worker_ready

# With worker_max_tasks_per_child=1 every task kills its child, and a task that
# arrives while all slots are dead sits in the worker until the pool-maintenance
# timer respawns children — hardcoded to 5.0s upstream (AsynPool.timers), which
# showed up as exact 5s dispatch stalls under load. maintain_pool() is a cheap
# no-op when nothing exited, so a 0.1s tick costs nothing and caps the stall.
AsynPool.timers = property(lambda self: {self.maintain_pool: 0.1})

# Upstream runs gc.collect() before every fork (issue #2927, a leak workaround
# for long-lived children). With one-task children and the parent heap frozen
# post-boot (see _freeze_parent_heap) there is nothing worth collecting, and at
# one fork per task the collect is pure per-task overhead on a 1-vCPU host.
_orig_create_worker_process = AsynPool._create_worker_process


def _create_worker_process_no_gc(self, i):
    _gc_collect, gc.collect = gc.collect, lambda *a: 0
    try:
        return _orig_create_worker_process(self, i)
    finally:
        gc.collect = _gc_collect


AsynPool._create_worker_process = _create_worker_process_no_gc

# Same in-container/localhost switch as backend/database/db_config.py: inside
# Docker the broker is reachable by service name, outside by published port.
_default_broker = (
    "redis://valkey:6379/0"
    if os.path.exists("/.dockerenv")
    else "redis://localhost:6379/0"
)
broker_url = os.environ.get("CELERY_BROKER_URL", _default_broker)
result_backend = os.environ.get("CELERY_RESULT_BACKEND", broker_url)

celery_app = Celery(
    "agent_games",
    broker=broker_url,
    backend=result_backend,
    include=[
        "backend.tasks.validation_task",
        "backend.tasks.simulation_task",
        "backend.tasks.exercise_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_routes={
        "validation.*": {"queue": "validation"},
        "simulation.*": {"queue": "simulation"},
    },
    # Fresh process per task: untrusted agent code can monkeypatch games.* or
    # leak module state — the process boundary is the isolation guarantee.
    worker_max_tasks_per_child=1,
    worker_prefetch_multiplier=1,
    # No task uses rate limits; skipping the per-task token-bucket bookkeeping
    # saves a little MainProcess CPU on the single shared core.
    worker_disable_rate_limits=True,
    result_expires=300,
    broker_connection_retry_on_startup=True,
    # Early acks: a hard-killed/OOM-killed child must never cause redelivery
    # of a poisonous agent task.
    task_acks_late=False,
)


# Fork-per-task makes fork cost the throughput ceiling on a 1-vCPU host: every
# page the child touches is copy-on-write-faulted, and the cyclic GC is the
# worst offender (a collection walks every tracked object, dirtying the whole
# inherited heap). Freeze the parent's heap into the permanent generation once
# it is fully booted so collections never traverse it, in parent or child.
@worker_ready.connect
def _freeze_parent_heap(**kwargs):
    gc.collect()
    gc.freeze()


# A child lives for exactly one short task (max_tasks_per_child=1): cyclic
# garbage cannot accumulate enough to matter, but a mid-task collection would
# COW-fault the inherited heap. Skip GC entirely for the child's lifetime.
@worker_process_init.connect
def _disable_gc_in_child(**kwargs):
    gc.disable()
