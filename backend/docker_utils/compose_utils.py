# backend/docker_utils/compose_utils.py
import logging
import os
import subprocess
import time
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def run_docker_compose_command(
    command: List[str], capture_output: bool = True
) -> subprocess.CompletedProcess:
    """Run a docker-compose command and return the result"""
    try:
        full_command = ["docker-compose"] + command
        logger.debug(f"Running docker-compose command: {' '.join(full_command)}")

        result = subprocess.run(
            full_command,
            check=False,  # Don't raise exception for non-zero exit code
            capture_output=capture_output,
            text=True,
        )
        return result
    except Exception as e:
        logger.error(f"Error running docker-compose command: {e}")
        raise


def get_container_logs(service_name: str) -> str:
    """Get logs from a Docker Compose service"""
    try:
        result = subprocess.run(
            ["docker-compose", "logs", service_name],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting logs for {service_name}: {e}")
        return f"Could not retrieve logs for {service_name}: {e}"

def restart_service(service_name: Optional[str] = None) -> bool:
    """Restart a specific service or all services"""
    try:
        cmd = ["docker-compose", "restart"]
        if service_name:
            cmd.append(service_name)
            logger.info(f"Restarting Docker Compose service: {service_name}")
        else:
            logger.info("Restarting all Docker Compose services")
        
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error restarting service(s): {e}")
        return False

def execute_command(service_name: str, command: str) -> str:
    """Execute a command in a Docker Compose service container"""
    try:
        result = subprocess.run(
            ["docker-compose", "exec", service_name, "sh", "-c", command],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing command in {service_name}: {e}")
        return f"Command execution failed: {e}"


def ensure_services_running() -> bool:
    """Ensure all services defined in docker-compose.yml are running"""
    try:
        # Check if services are already running
        ps_result = run_docker_compose_command(
            ["ps", "--services", "--filter", "status=running"]
        )
        running_services = (
            set(ps_result.stdout.strip().split("\n"))
            if ps_result.stdout.strip()
            else set()
        )

        # Get all services from config
        config_result = run_docker_compose_command(["config", "--services"])
        all_services = (
            set(config_result.stdout.strip().split("\n"))
            if config_result.stdout.strip()
            else set()
        )

        # Find services that aren't running
        not_running = all_services - running_services
        if not_running:
            logger.info(f"Starting services: {', '.join(not_running)}")

            # Try to start just the non-running services first
            for service in not_running:
                run_docker_compose_command(["up", "-d", service])

            # Verify they're running now
            ps_result = run_docker_compose_command(
                ["ps", "--services", "--filter", "status=running"]
            )
            running_after = (
                set(ps_result.stdout.strip().split("\n"))
                if ps_result.stdout.strip()
                else set()
            )

            if all_services != running_after:
                # Some services still not running, try starting everything
                logger.warning(
                    "Not all services started. Attempting to start all services..."
                )
                run_docker_compose_command(["up", "-d"])

                # Final verification
                ps_result = run_docker_compose_command(
                    ["ps", "--services", "--filter", "status=running"]
                )
                final_running = (
                    set(ps_result.stdout.strip().split("\n"))
                    if ps_result.stdout.strip()
                    else set()
                )

                if all_services != final_running:
                    logger.error(
                        f"Failed to start services: {', '.join(all_services - final_running)}"
                    )
                    return False

        logger.info("All required services are running")
        return True

    except Exception as e:
        logger.error(f"Error ensuring services are running: {e}")
        return False


def stop_services() -> bool:
    """Stop all services defined in docker-compose.yml"""
    try:
        run_docker_compose_command(["down"])
        logger.info("All services stopped")
        return True
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
        inspect_cmd = [
            "docker",
            "inspect",
            f"$(docker-compose ps -q {service_name})",
            "-f",
            "{{.State.Health.Status}}",
        ]

        # Use shell=True as we're using shell syntax for substitution
        health_result = subprocess.run(
            " ".join(inspect_cmd), shell=True, capture_output=True, text=True
        )

        if health_result.returncode == 0 and health_result.stdout.strip() == "healthy":
            return True, f"Service {service_name} is healthy"
        elif "no such field" in health_result.stderr:
            # Service doesn't have a health check defined, just check if it's running
            return True, f"Service {service_name} is running (no health check defined)"
        else:
            return (
                False,
                f"Service {service_name} is not healthy: {health_result.stdout.strip() or health_result.stderr.strip()}",
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
        # Get all services from config
        config_result = run_docker_compose_command(["config", "--services"])
        all_services = (
            config_result.stdout.strip().split("\n")
            if config_result.stdout.strip()
            else []
        )

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
