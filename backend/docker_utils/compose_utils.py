import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

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