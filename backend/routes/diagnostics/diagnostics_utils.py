import logging
import os
from typing import Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# Service URLs for health checks
SERVICE_URLS = {
    "validator": "http://validator:8001",
    "simulator": "http://simulator:8002",
}

# Log file paths
LOG_DIR = "/agent_games/logs"
LOG_FILES = {
    "validator": os.path.join(LOG_DIR, "validator.log"),
    "simulator": os.path.join(LOG_DIR, "simulator.log"),
    "api": os.path.join(LOG_DIR, "api.log"),
}


def get_service_logs(service_name: str, tail: Optional[int] = 1000) -> str:
    """
    Get logs for a specific service from log files

    Args:
        service_name: Name of the service to get logs for
        tail: Number of log lines to return (default: 1000)

    Returns:
        Logs as a string
    """
    try:
        log_file = LOG_FILES.get(service_name)
        if not log_file:
            return f"Unknown service: {service_name}"

        if not os.path.exists(log_file):
            # MINIMAL ADDITION: Better error message
            return f"Log file not found: {log_file}\nRun './setup_logs.sh' to create log files first."

        # Read the last 'tail' lines from the log file
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        # Return the last 'tail' lines
        if tail and len(lines) > tail:
            lines = lines[-tail:]

        # MINIMAL ADDITION: Handle empty files
        return "".join(lines) if lines else f"Log file {log_file} is empty"

    except Exception as e:
        error_msg = f"Error reading log file for {service_name}: {str(e)}"
        logger.error(error_msg)
        return error_msg


async def check_service_health_http(service_name: str) -> Tuple[bool, str]:
    """
    Check if a service is healthy using HTTP health endpoint
    Returns (is_healthy, message)
    """
    try:
        service_url = SERVICE_URLS.get(service_name)
        if not service_url:
            return False, f"Unknown service: {service_name}"

        health_url = f"{service_url}/health"

        async with httpx.AsyncClient() as client:
            response = await client.get(health_url, timeout=5.0)

            if response.status_code == 200:
                return True, f"Service {service_name} is healthy (HTTP 200)"
            else:
                return (
                    False,
                    f"Service {service_name} returned HTTP {response.status_code}",
                )

    except httpx.ConnectError:
        return False, f"Service {service_name} is unreachable (connection refused)"
    except httpx.TimeoutException:
        return False, f"Service {service_name} health check timed out"
    except Exception as e:
        error_msg = f"Error checking health of service {service_name}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def get_all_services_status() -> Dict[str, Dict]:
    """
    Get status information for validator and simulator services using HTTP health checks

    Returns:
        Dictionary mapping service names to their status information
    """
    services = ["validator", "simulator"]
    statuses = {}

    for service in services:
        is_healthy, health_message = await check_service_health_http(service)

        # Determine status based on health check
        status = "running" if is_healthy else "unhealthy"

        statuses[service] = {
            "name": service,
            "status": status,
            "health": health_message,
            "is_healthy": is_healthy,
        }

    return statuses
