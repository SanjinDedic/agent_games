import os

from celery import Celery

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
        "backend.routes.user.code_validation",
        "backend.games.simulation_task",
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
    # If this is ever relaxed, the simulation task's per-child DB engine
    # assumption breaks too (see backend/games/simulation_task.py).
    worker_max_tasks_per_child=1,
    worker_prefetch_multiplier=1,
    result_expires=300,
    broker_connection_retry_on_startup=True,
    # Early acks: a hard-killed/OOM-killed child must never cause redelivery
    # of a poisonous agent task.
    task_acks_late=False,
)
