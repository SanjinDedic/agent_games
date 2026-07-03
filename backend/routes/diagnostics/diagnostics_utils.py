import asyncio
import logging
from typing import Dict

from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Worker node-name prefixes (workers are launched with -n validation@%h /
# -n simulation@%h) mapped to the status entries the frontend renders.
WORKER_SERVICES = {
    "validation": "validation-worker",
    "simulation": "simulation-worker",
}


def _entry(name: str, is_healthy: bool, health: str) -> Dict:
    return {
        "name": name,
        "status": "running" if is_healthy else "unhealthy",
        "health": health,
        "is_healthy": is_healthy,
    }


def _collect_statuses() -> Dict[str, Dict]:
    statuses: Dict[str, Dict] = {}

    # Broker reachability
    try:
        with celery_app.connection_for_read() as conn:
            conn.ensure_connection(max_retries=1, timeout=2)
        statuses["valkey"] = _entry("valkey", True, "Broker connection OK")
    except Exception as e:
        error_msg = f"Broker unreachable: {str(e)}"
        logger.error(error_msg)
        statuses["valkey"] = _entry("valkey", False, error_msg)
        for service_name in WORKER_SERVICES.values():
            statuses[service_name] = _entry(service_name, False, error_msg)
        return statuses

    # Worker pings
    try:
        replies = celery_app.control.inspect(timeout=2.0).ping() or {}
    except Exception as e:
        replies = {}
        logger.error(f"Worker ping failed: {str(e)}")

    for prefix, service_name in WORKER_SERVICES.items():
        node = next((n for n in replies if n.startswith(f"{prefix}@")), None)
        if node:
            statuses[service_name] = _entry(
                service_name, True, f"Worker {node} responded to ping"
            )
        else:
            statuses[service_name] = _entry(
                service_name, False, f"No {prefix} worker responded to ping"
            )

    return statuses


async def get_all_services_status() -> Dict[str, Dict]:
    """Get status for the Celery broker and both worker types.

    Returns a dictionary mapping service names to their status information;
    each entry has the {name, status, health, is_healthy} shape the frontend
    renders.
    """
    return await asyncio.to_thread(_collect_statuses)
