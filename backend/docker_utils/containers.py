import json
import logging
import os
import subprocess
import time
import traceback

from backend.config import ROOT_DIR

logger = logging.getLogger(__name__)

CONTAINERS = {
    "validator": {
        "dockerfile": "docker_utils/dockerfiles/validator.dockerfile",
    },
    "simulator": {
        "dockerfile": "docker_utils/dockerfiles/simulator.dockerfile",
    },
}


def get_container_logs(container_name: str) -> str:
    """Get the logs from a container"""
    try:
        result = subprocess.run(
            ["docker", "logs", container_name],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return "Could not retrieve container logs"


def stop_containers():
    """Stop and remove running containers"""
    logger.info(f"Stopping containers called from: {traceback.extract_stack()[-2]}")
    for container_name in CONTAINERS:
        try:
            # Check if container exists
            result = subprocess.run(
                ["docker", "ps", "-a", "-q", "-f", f"name={container_name}"],
                capture_output=True,
                text=True,
            )

            if result.stdout.strip():
                logger.info(f"Stopping {container_name} container...")
                # Stop the container
                subprocess.run(
                    ["docker", "stop", container_name], check=True, capture_output=True
                )
                # Remove the container
                subprocess.run(
                    ["docker", "rm", container_name], check=True, capture_output=True
                )
                logger.info(f"{container_name} container stopped and removed")

        except subprocess.CalledProcessError as e:
            logger.error(f"Error stopping {container_name} container: {e}")
            logger.error(f"Command output: {e.output}")
        except Exception as e:
            logger.error(f"Unexpected error stopping {container_name} container: {e}")


def ensure_containers_running():
    """Ensure both validator and simulator containers are running, building images if needed"""
    for container_name, config in CONTAINERS.items():
        try:
            # First, clean up any existing stopped container
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                check=False,  # Don't fail if container doesn't exist
            )

            # Check if image exists
            result = subprocess.run(
                ["docker", "images", "-q", container_name],
                capture_output=True,
                text=True,
            )

            # Build image if it doesn't exist
            if not result.stdout.strip():
                logger.info(f"Building {container_name} image...")
                subprocess.run(
                    [
                        "docker",
                        "build",
                        "-t",
                        container_name,
                        "-f",
                        config["dockerfile"],
                        ".",
                    ],
                    check=True,
                    cwd=ROOT_DIR,
                )

            # Start container with host network
            logger.info(f"Starting {container_name} container...")
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    container_name,
                    "--network=host",
                    "-v",
                    # Updated mount path
                    f"{ROOT_DIR}:/agent_games/backend:ro",
                    "-e",
                    f"SERVICE_TOKEN={os.getenv('SERVICE_TOKEN')}",
                    "-e",
                    f"SECRET_KEY={os.getenv('SECRET_KEY')}",
                    "--restart=on-failure:3",
                    container_name,
                ],
                check=True,
            )

            # Wait briefly for container to start
            time.sleep(2)

            # Check container status
            inspect_result = subprocess.run(
                ["docker", "inspect", container_name],
                capture_output=True,
                text=True,
            )

            if inspect_result.returncode == 0:
                container_info = json.loads(inspect_result.stdout)
                if not container_info[0]["State"]["Running"]:
                    logs = get_container_logs(container_name)
                    logger.error(
                        f"{container_name} failed to start. Container logs:\n{logs}"
                    )
                    raise RuntimeError(f"{container_name} container failed to start")
                logger.info(f"{container_name} container started successfully")
            else:
                raise RuntimeError(f"Could not inspect {container_name} container")

        except subprocess.CalledProcessError as e:
            logger.error(f"Docker command failed for {container_name}: {e}")
            logger.error(f"Command output: {e.output}")
            logs = get_container_logs(container_name)
            logger.error(f"Container logs:\n{logs}")
            raise RuntimeError(f"Failed to manage {container_name} container: {e}")
        except Exception as e:
            logger.error(f"Error managing {container_name} container: {e}")
            logs = get_container_logs(container_name)
            logger.error(f"Container logs:\n{logs}")
            raise RuntimeError(f"Error managing {container_name} container: {e}")
