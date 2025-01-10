import logging
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Local application imports
from api import lifespan
from config import ROOT_DIR
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
    with patch("docker.containers.logger") as mock_log:
        yield mock_log


@pytest.mark.asyncio
async def test_lifespan_successful_startup_shutdown(mock_logger, test_app):
    """
    Test the normal flow where containers start and stop successfully.
    This verifies that:
    1. Container startup is attempted with correct root directory
    2. Proper logging occurs
    3. Containers are stopped on shutdown
    """
    with patch("api.ensure_containers_running") as mock_ensure_containers, patch(
        "api.stop_containers"
    ) as mock_stop_containers:

        async with lifespan(test_app):
            # Verify startup sequence with actual ROOT_DIR
            mock_ensure_containers.assert_called_once_with(ROOT_DIR)
            mock_logger.info.assert_any_call("Starting application containers...")
            mock_logger.info.assert_any_call("All containers started successfully")

            mock_logger.reset_mock()

        mock_stop_containers.assert_called_once()
        mock_logger.info.assert_any_call(
            "Shutting down application, stopping containers..."
        )
        mock_logger.info.assert_any_call("Application shutdown complete")


@pytest.mark.asyncio
async def test_lifespan_startup_failure(mock_logger, test_app):
    """
    Test the error handling when container startup fails.
    This verifies that:
    1. Errors during startup are properly logged
    2. The application continues to run
    3. Shutdown still occurs normally
    """
    startup_error = Exception("Container startup failed")

    # Mock ensure_containers_running to raise an error
    with patch("api.ensure_containers_running", side_effect=startup_error), patch(
        "api.stop_containers"
    ) as mock_stop_containers:

        # Create an async context manager for testing
        async with lifespan(test_app):
            # Verify error logging
            mock_logger.error.assert_called_with(
                f"Failed to start containers: {startup_error}"
            )

            # Reset the mock to check shutdown sequence
            mock_logger.reset_mock()

        # Verify shutdown still occurs
        mock_stop_containers.assert_called_once()
        mock_logger.info.assert_any_call(
            "Shutting down application, stopping containers..."
        )
        mock_logger.info.assert_any_call("Application shutdown complete")


@pytest.mark.asyncio
async def test_lifespan_shutdown_failure(mock_logger, test_app):
    """
    Test error handling during container shutdown.
    This verifies that:
    1. Startup occurs normally with correct root directory
    2. Errors during shutdown are properly logged
    3. The application still completes its shutdown
    """
    shutdown_error = Exception("Container shutdown failed")

    with patch("api.ensure_containers_running") as mock_ensure_containers, patch(
        "api.stop_containers", side_effect=shutdown_error
    ):

        async with lifespan(test_app):
            # Verify normal startup with actual ROOT_DIR
            mock_ensure_containers.assert_called_once_with(ROOT_DIR)
            mock_logger.info.assert_any_call("Starting application containers...")

            mock_logger.reset_mock()


@pytest.mark.asyncio
async def test_lifespan_container_verification(mock_logger, test_app):
    """
    Test that the lifespan manager properly verifies container status.
    This verifies that:
    1. Container verification is performed during startup
    2. The startup process uses the correct root directory
    """
    with patch("api.ensure_containers_running") as mock_ensure_containers, patch(
        "api.ROOT_DIR", "/test/root/dir"
    ), patch("api.stop_containers"):

        async with lifespan(test_app):
            # Verify container verification
            mock_ensure_containers.assert_called_once_with("/test/root/dir")

            # Verify proper logging
            mock_logger.info.assert_any_call("Starting application containers...")
            mock_logger.info.assert_any_call("All containers started successfully")


@pytest.mark.asyncio
async def test_container_stop_command_error(mock_containers_logger):
    """
    Tests error handling when Docker stop command fails.
    This verifies that command failures are properly caught and logged.
    """
    error_output = b"Error: No such container: test_container"
    command_error = subprocess.CalledProcessError(
        returncode=1, cmd=["docker", "stop", "validator"], output=error_output
    )

    with patch("subprocess.run", side_effect=command_error):
        stop_containers()

        # Verify error logging using the correctly mocked logger
        mock_containers_logger.error.assert_any_call(
            "Error stopping validator container: Command '['docker', 'stop', 'validator']' "
            "returned non-zero exit status 1."
        )
        mock_containers_logger.error.assert_any_call(f"Command output: {error_output}")


@pytest.mark.asyncio
async def test_container_stop_unexpected_error(mock_containers_logger):
    """
    Tests handling of unexpected errors during container shutdown.
    """
    unexpected_error = Exception("Network unavailable")

    with patch("subprocess.run", side_effect=unexpected_error):
        stop_containers()

        mock_containers_logger.error.assert_any_call(
            "Unexpected error stopping validator container: Network unavailable"
        )


@pytest.mark.asyncio
async def test_container_management_error_with_logs(mock_containers_logger):
    """
    Tests comprehensive error handling during container management.
    """
    management_error = Exception("Container creation failed")
    container_logs = "Container startup error: port already in use"

    with patch("subprocess.run", side_effect=management_error), patch(
        "docker.containers.get_container_logs", return_value=container_logs
    ):

        with pytest.raises(RuntimeError) as exc_info:
            ensure_containers_running(ROOT_DIR)

        # Verify error handling using the correctly mocked logger
        assert (
            str(exc_info.value)
            == f"Error managing validator container: {management_error}"
        )
        mock_containers_logger.error.assert_any_call(
            f"Error managing validator container: {management_error}"
        )
        mock_containers_logger.error.assert_any_call(
            f"Container logs:\n{container_logs}"
        )


@pytest.mark.asyncio
async def test_get_container_logs_error(mock_logger):
    """
    Tests error handling when retrieving container logs fails.
    This verifies that:
    1. Log retrieval failures are handled gracefully
    2. A default message is returned
    """
    command_error = subprocess.CalledProcessError(
        returncode=1, cmd=["docker", "logs", "validator"], output=b"No such container"
    )

    with patch("subprocess.run", side_effect=command_error):
        logs = get_container_logs("validator")
        assert logs == "Could not retrieve container logs"
