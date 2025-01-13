import logging
import subprocess
from unittest.mock import patch

import pytest
from api import lifespan
from docker_utils.containers import (
    ensure_containers_running,
    get_container_logs,
    stop_containers,
)
from fastapi import FastAPI


@pytest.fixture
def mock_logger():
    with patch("api.logger") as mock_log:
        yield mock_log


@pytest.fixture
def test_app():
    return FastAPI()


@pytest.fixture
def mock_containers_logger():
    """Fixture to provide a mock logger for the containers module"""
    with patch("docker_utils.containers.logger") as mock_log:
        yield mock_log


@pytest.mark.asyncio
async def test_lifespan_successful_startup_shutdown(mock_logger, test_app):
    """Test successful container startup and shutdown"""
    with patch(
        "docker_utils.containers.ensure_containers_running"
    ) as mock_ensure_containers, patch(
        "docker_utils.containers.stop_containers"
    ) as mock_stop_containers:

        async with lifespan(test_app):
            # Verify startup sequence
            mock_ensure_containers.assert_called_once()
            mock_logger.info.assert_any_call("Starting application containers...")
            mock_logger.info.assert_any_call("All containers started successfully")

            mock_logger.reset_mock()

        # Verify shutdown sequence
        mock_stop_containers.assert_called_once()
        mock_logger.info.assert_any_call(
            "Shutting down application, stopping containers..."
        )
        mock_logger.info.assert_any_call("Application shutdown complete")


@pytest.mark.asyncio
async def test_lifespan_startup_failure(mock_logger, test_app):
    """Test error handling during container startup"""
    startup_error = Exception("Container startup failed")

    with patch(
        "docker_utils.containers.ensure_containers_running", side_effect=startup_error
    ), patch("docker_utils.containers.stop_containers") as mock_stop_containers:

        async with lifespan(test_app):
            mock_logger.error.assert_called_with(
                f"Failed to start containers: {startup_error}"
            )
            mock_logger.reset_mock()

        mock_stop_containers.assert_called_once()
        mock_logger.info.assert_any_call(
            "Shutting down application, stopping containers..."
        )


@pytest.mark.asyncio
async def test_lifespan_shutdown_failure(mock_logger, test_app):
    """Test error handling during container shutdown"""
    shutdown_error = Exception("Container shutdown failed")

    with patch(
        "docker_utils.containers.ensure_containers_running"
    ) as mock_ensure_containers, patch(
        "docker_utils.containers.stop_containers", side_effect=shutdown_error
    ):

        async with lifespan(test_app):
            mock_ensure_containers.assert_called_once()
            mock_logger.info.assert_any_call("Starting application containers...")
            mock_logger.reset_mock()

        mock_logger.error.assert_called_with(
            f"Error during container shutdown: {shutdown_error}"
        )


@pytest.mark.asyncio
async def test_container_stop_command_error(mock_containers_logger):
    """Test error handling for Docker stop command failures"""
    error_output = b"Error: No such container: test_container"
    command_error = subprocess.CalledProcessError(
        returncode=1, cmd=["docker", "stop", "validator"], output=error_output
    )

    with patch("subprocess.run", side_effect=command_error):
        stop_containers()

        mock_containers_logger.error.assert_any_call(
            "Error stopping validator container: Command '['docker', 'stop', 'validator']' "
            "returned non-zero exit status 1."
        )


@pytest.mark.asyncio
async def test_get_container_logs_error():
    """Test error handling for container log retrieval"""
    command_error = subprocess.CalledProcessError(
        returncode=1, cmd=["docker", "logs", "validator"], output=b"No such container"
    )

    with patch("subprocess.run", side_effect=command_error):
        logs = get_container_logs("validator")
        assert logs == "Could not retrieve container logs"
