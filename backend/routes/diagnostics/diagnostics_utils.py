import asyncio
import logging
from typing import Dict

import redis

from backend.config import VALKEY_URL

logger = logging.getLogger(__name__)


def _entry(name: str, is_healthy: bool, health: str) -> Dict:
    return {
        "name": name,
        "status": "running" if is_healthy else "unhealthy",
        "health": health,
        "is_healthy": is_healthy,
    }


def _collect_statuses() -> Dict[str, Dict]:
    """Health of the backing services the API depends on.

    Only Valkey remains: all code execution happens in the browser (Pyodide)
    or on Lambdas the browser calls directly (backend/lambda_fallback/validation/,
    backend/lambda_fallback/exercise_snippet/) — neither has a long-lived service to ping.
    """
    statuses: Dict[str, Dict] = {}
    try:
        client = redis.Redis.from_url(
            VALKEY_URL, socket_connect_timeout=2, socket_timeout=2
        )
        try:
            client.ping()
        finally:
            client.close()
        statuses["valkey"] = _entry("valkey", True, "Valkey connection OK")
    except Exception as e:
        error_msg = f"Valkey unreachable: {str(e)}"
        logger.error(error_msg)
        statuses["valkey"] = _entry("valkey", False, error_msg)
    return statuses


async def get_all_services_status() -> Dict[str, Dict]:
    """Get status for the backing services.

    Returns a dictionary mapping service names to their status information;
    each entry has the {name, status, health, is_healthy} shape the frontend
    renders.
    """
    return await asyncio.to_thread(_collect_statuses)
