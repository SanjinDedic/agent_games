import json
import subprocess
from unittest.mock import Mock, call, patch

import httpx
import pytest

from backend.docker_utils.compose_utils import ensure_services_running, stop_services


def test_validator_container_health():
    """Verify the validator container is running and healthy"""
    import asyncio

    async def check_health():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8001/health")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
        except httpx.RequestError as e:
            pytest.fail(
                f"Validator container is not running or not accessible: {str(e)}"
            )

    asyncio.run(check_health())


def test_simulator_container_health():
    """Verify the simulator container is running and healthy"""
    import asyncio

    async def check_health():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8002/health")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
        except httpx.RequestError as e:
            pytest.fail(
                f"Simulator container is not running or not accessible: {str(e)}"
            )

    asyncio.run(check_health())


def test_ensure_services_running_success():
    """Test that services get started when not already running"""

    with patch(
        "backend.docker_utils.compose_utils.run_docker_compose_command"
    ) as mock_run_cmd:
        # Create a custom side effect function that returns different results
        run_count = {"value": 0}

        def custom_side_effect(*args, **kwargs):
            run_count["value"] += 1
            command = args[0]

            # First call: get_services() calls config --services
            if run_count["value"] == 1 and command == ["config", "--services"]:
                return Mock(returncode=0, stdout="validator\nsimulator\n", stderr="")

            # Second call: get_running_services() calls ps
            elif run_count["value"] == 2 and command == [
                "ps",
                "--services",
                "--filter",
                "status=running",
            ]:
                return Mock(returncode=0, stdout="", stderr="")  # No services running

            # Third call: Trigger docker-compose up -d
            elif command == ["up", "-d"]:
                return Mock(returncode=0, stdout="", stderr="")

            # Fourth call: Check running services again after start attempt
            elif run_count["value"] > 3 and command == [
                "ps",
                "--services",
                "--filter",
                "status=running",
            ]:
                return Mock(
                    returncode=0, stdout="validator\nsimulator\n", stderr=""
                )  # Now services are running

            # Default fallback
            return Mock(returncode=0, stdout="", stderr="")

        # Set the side effect
        mock_run_cmd.side_effect = custom_side_effect

        # Run the function we're testing
        result = ensure_services_running()

        # Verify it returned success
        assert result is True

        # Check correct commands were called
        call_args_list = mock_run_cmd.call_args_list
        commands_called = [args[0][0] for args in call_args_list]

        # Verify the sequence of commands
        assert [
            "config",
            "--services",
        ] in commands_called, "Should check available services"
        assert [
            "ps",
            "--services",
            "--filter",
            "status=running",
        ] in commands_called, "Should check running services"
        assert [
            "up",
            "-d",
        ] in commands_called, "Should start services with up -d command"

@patch("subprocess.run")
def test_ensure_services_running_failure(mock_subprocess_run):
    """Test handling service startup failure"""
    # Mock command execution error
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        1, "docker-compose up -d", output=b"Failed to start services"
    )

    # Should return False on failure
    result = ensure_services_running()
    assert result is False


@patch("subprocess.run")
def test_stop_services(mock_subprocess_run):
    """Test stopping services with Docker Compose"""
    # Mock successful down command
    mock_subprocess_run.return_value.returncode = 0

    # Call the function
    result = stop_services()

    # Verify it returned true
    assert result is True

    # Check that docker-compose down was called
    mock_subprocess_run.assert_called_with(
        ["docker-compose", "down"], check=False, capture_output=True, text=True
    )


@patch("subprocess.run")
def test_stop_services_failure(mock_subprocess_run):
    """Test handling service shutdown failure"""
    # Mock command execution error
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        1, "docker-compose down", output=b"Failed to stop services"
    )

    # Should return False on failure
    result = stop_services()
    assert result is False


if __name__ == "__main__":
    pytest.main(["-v"])
