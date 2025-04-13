import logging
import subprocess
import time
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def run_docker_compose_command(
    command: List[str], capture_output: bool = True
) -> subprocess.CompletedProcess:
    """Run a docker compose command and return the result"""
    try:
        full_command = [
            "docker",
            "compose",
        ] + command  # Changed from ["docker-compose"]
        logger.debug(f"Running docker compose command: {' '.join(full_command)}")

        result = subprocess.run(
            full_command,
            check=False,  # Don't raise exception for non-zero exit code
            capture_output=capture_output,
            text=True,
        )
        return result
    except Exception as e:
        logger.error(f"Error running docker compose command: {e}")
        raise


def get_container_logs(service_name: str) -> str:
    """Get logs from a Docker Compose service"""
    try:
        result = run_docker_compose_command(["logs", service_name])
        return result.stdout
    except Exception as e:
        logger.error(f"Error getting logs for {service_name}: {e}")
        return f"Could not retrieve logs for {service_name}: {e}"


def restart_service(service_name: Optional[str] = None) -> bool:
    """
    Restart a specific service or all services

    Note: This operation may be blocked by Docker Socket Proxy
    if it's configured to block POST operations
    """
    try:
        cmd = ["restart"]
        if service_name:
            cmd.append(service_name)
            logger.info(f"Attempting to restart Docker Compose service: {service_name}")
        else:
            logger.info("Attempting to restart all Docker Compose services")

        result = run_docker_compose_command(cmd)

        if result.returncode != 0 and "403 Forbidden" in result.stderr:
            logger.warning(
                "Restart operation blocked by Docker Socket Proxy (permission denied)"
            )
            return False

        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error restarting service(s): {e}")
        return False


def execute_command(service_name: str, command: str) -> str:
    """Execute a command in a Docker Compose service container"""
    try:
        result = run_docker_compose_command(["exec", service_name, "sh", "-c", command])
        return result.stdout
    except Exception as e:
        logger.error(f"Error executing command in {service_name}: {e}")
        return f"Command execution failed: {e}"


def get_services() -> List[str]:
    """Get all services defined in docker-compose.yml"""
    config_result = run_docker_compose_command(["config", "--services"])
    return (
        config_result.stdout.strip().split("\n") if config_result.stdout.strip() else []
    )


def get_running_services() -> List[str]:
    """Get all currently running services"""
    ps_result = run_docker_compose_command(
        ["ps", "--services", "--filter", "status=running"]
    )
    return ps_result.stdout.strip().split("\n") if ps_result.stdout.strip() else []


def ensure_services_running() -> bool:
    """
    Ensure all services defined in docker-compose.yml are running

    Note: This operation may be blocked by Docker Socket Proxy
    if it's configured to block POST operations
    """
    try:
        # Get services that should be running and those that are running
        all_services = set(get_services())
        running_services = set(get_running_services())

        # Start any non-running services
        not_running = all_services - running_services
        if not_running:
            logger.info(f"Attempting to start services: {', '.join(not_running)}")

            # Directly start all services - simpler than individual starts
            result = run_docker_compose_command(["up", "-d"])

            if result.returncode != 0 and "403 Forbidden" in result.stderr:
                logger.warning(
                    "Service start operation blocked by Docker Socket Proxy (permission denied)"
                )
                logger.warning(
                    "Services may need to be started manually or by an administrator"
                )
                return False

            # Verify everything started
            running_after = set(get_running_services())
            if all_services != running_after:
                not_started = all_services - running_after
                logger.error(f"Failed to start services: {', '.join(not_started)}")
                return False

        logger.info("All required services are running")
        return True
    except Exception as e:
        logger.error(f"Error ensuring services are running: {e}")
        return False


def stop_services() -> bool:
    """
    Stop all services defined in docker-compose.yml

    Note: This operation may be blocked by Docker Socket Proxy
    if it's configured to block POST operations
    """
    try:
        result = run_docker_compose_command(["down"])

        if result.returncode != 0 and "403 Forbidden" in result.stderr:
            logger.warning(
                "Service stop operation blocked by Docker Socket Proxy (permission denied)"
            )
            logger.warning(
                "Services may need to be stopped manually or by an administrator"
            )
            return False

        logger.info("All services stopped")
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error stopping services: {e}")
        return False


def check_service_health(service_name: str) -> Tuple[bool, str]:
    """
    Check if a service is healthy using docker-compose
    Returns (is_healthy, message)
    """
    try:
        # Check if service is running
        ps_result = run_docker_compose_command(["ps", service_name])
        if "Up" not in ps_result.stdout:
            return False, f"Service {service_name} is not running"

        # For services with healthcheck, inspect the container
        container_id = run_docker_compose_command(
            ["ps", "-q", service_name]
        ).stdout.strip()
        if not container_id:
            return False, f"Cannot find container ID for service {service_name}"

        # Use docker inspect with the new command structure
        inspect_result = subprocess.run(
            ["docker", "inspect", container_id, "-f", "{{.State.Health.Status}}"],
            capture_output=True,
            text=True,
            check=False,
        )

        if inspect_result.returncode == 0:
            status = inspect_result.stdout.strip()
            if status == "healthy":
                return True, f"Service {service_name} is healthy"
            elif status:  # Has a health status but not "healthy"
                return False, f"Service {service_name} health status: {status}"
            else:  # Empty result usually means no health check defined
                return (
                    True,
                    f"Service {service_name} is running (no health check defined)",
                )
        else:
            # If inspect command failed, check if container exists
            return (
                True,
                f"Service {service_name} is running (unable to check health status)",
            )

    except Exception as e:
        error_msg = f"Error checking health of service {service_name}: {e}"
        logger.error(error_msg)
        return False, error_msg


def verify_all_services_healthy() -> Tuple[bool, Dict[str, str]]:
    """
    Verify that all services defined in docker-compose are healthy
    Returns (all_healthy, status_dict)
    """
    try:
        all_services = get_services()
        all_healthy = True
        service_status = {}

        for service in all_services:
            is_healthy, message = check_service_health(service)
            service_status[service] = message
            if not is_healthy:
                all_healthy = False

        return all_healthy, service_status

    except Exception as e:
        error_msg = f"Error verifying service health: {e}"
        logger.error(error_msg)
        return False, {"error": error_msg}


def wait_for_services(timeout: int = 60, interval: int = 5) -> bool:
    """
    Wait for all services to be running and healthy

    Args:
        timeout: Maximum time to wait in seconds
        interval: Time between health checks in seconds

    Returns:
        bool: True if all services are healthy, False otherwise
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        # First ensure all services are running
        if not ensure_services_running():
            logger.warning("Not all services are running yet, waiting...")
            time.sleep(interval)
            continue

        # Then check if they're all healthy
        is_healthy, statuses = verify_all_services_healthy()
        if is_healthy:
            logger.info("All services are healthy")
            return True

        # Log current status
        unhealthy = [
            svc for svc, msg in statuses.items() if "not healthy" in msg.lower()
        ]
        if unhealthy:
            logger.warning(f"Services still unhealthy: {', '.join(unhealthy)}")

        time.sleep(interval)

    logger.error(
        f"Timed out waiting for services to be healthy after {timeout} seconds"
    )
    return False
