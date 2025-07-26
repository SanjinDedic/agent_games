import subprocess
from unittest.mock import patch

import pytest
from fastapi import FastAPI

from backend.api import lifespan


@pytest.fixture
def mock_logger():
    with patch("backend.api.logger") as mock_log:
        yield mock_log


@pytest.fixture
def test_app():
    return FastAPI()


def get_container_logs_direct(service_name: str, tail: int = 100) -> str:
    """Direct replacement for removed get_container_logs function"""
    try:
        result = subprocess.run(
            ["docker", "compose", "logs", "--tail", str(tail), service_name],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Could not retrieve logs for {service_name}: {e}"


@pytest.mark.asyncio
async def test_lifespan_successful_startup_shutdown(mock_logger, test_app):
    """Test successful application startup and shutdown"""
    async with lifespan(test_app):
        # Verify startup message
        mock_logger.info.assert_any_call("Starting application...")

        mock_logger.reset_mock()

    # Verify shutdown message
    mock_logger.info.assert_any_call("Shutting down application...")


@pytest.mark.asyncio
async def test_lifespan_startup_exception(mock_logger, test_app):
    """Test error handling during application startup"""
    startup_error = Exception("Application startup failed")

    with patch.object(mock_logger, "info", side_effect=startup_error):
        async with lifespan(test_app):
            mock_logger.error.assert_called_with(
                f"Failed to start application: {startup_error}"
            )


@pytest.mark.asyncio
async def test_get_service_logs():
    """Test getting service logs using direct docker compose command"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "Test log output"
        mock_run.return_value.returncode = 0

        logs = get_container_logs_direct("validator")
        assert logs == "Test log output"

        # Verify docker-compose logs command was called
        cmd_args = mock_run.call_args[0][0]
        assert "docker" in cmd_args
        assert "compose" in cmd_args
        assert "logs" in cmd_args
        assert "validator" in cmd_args


@pytest.mark.asyncio
async def test_get_service_logs_error():
    """Test error handling for service log retrieval"""
    command_error = subprocess.CalledProcessError(
        returncode=1,
        cmd=["docker", "compose", "logs", "validator"],
        output=b"No such service: validator",
    )

    with patch("subprocess.run", side_effect=command_error):
        logs = get_container_logs_direct("validator")
        assert "Could not retrieve logs" in logs
