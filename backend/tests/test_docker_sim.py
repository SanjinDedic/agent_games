import json
import subprocess
from unittest.mock import patch

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


import subprocess
from unittest.mock import Mock, call, patch

import pytest

from backend.docker_utils.compose_utils import ensure_services_running


def test_ensure_services_running_success():
    """Test that services get started when not already running"""

    with patch("subprocess.run") as mock_run:
        # Create a custom side effect function that returns different results
        # based on which command is being called
        run_count = {"value": 0}

        def custom_side_effect(*args, **kwargs):
            run_count["value"] += 1
            command = args[0]

            # Convert command list to string for easier matching
            cmd_str = " ".join(command)

            # First call: Check running services - return empty (none running)
            if (
                run_count["value"] == 1
                and "ps --services --filter status=running" in cmd_str
            ):
                return Mock(returncode=0, stdout="", stderr="")

            # Second call: Get list of services - return validator and simulator
            elif run_count["value"] == 2 and "config --services" in cmd_str:
                return Mock(returncode=0, stdout="validator\nsimulator\n", stderr="")

            # Service start calls
            elif "up -d" in cmd_str:
                return Mock(returncode=0, stdout="", stderr="")

            # Later calls: Check running services again - return services as running
            elif (
                run_count["value"] > 2
                and "ps --services --filter status=running" in cmd_str
            ):
                return Mock(returncode=0, stdout="validator\nsimulator\n", stderr="")

            # Default fallback
            return Mock(returncode=0, stdout="", stderr="")

        # Set the side effect
        mock_run.side_effect = custom_side_effect

        # Run the function we're testing
        result = ensure_services_running()

        # Verify it returned success
        assert result is True

        # Check correct commands were called
        call_list = [" ".join(call_args[0][0]) for call_args in mock_run.call_args_list]

        # Verify the sequence of commands (this is the key check!)
        assert any(
            "ps --services --filter status=running" in call for call in call_list
        ), "Should check for running services"
        assert any(
            "config --services" in call for call in call_list
        ), "Should get available services"
        assert any(
            "up -d" in call for call in call_list
        ), "Should start services with up -d command"

        # Make sure up command was called after initial ps check
        ps_index = next(
            i
            for i, call in enumerate(call_list)
            if "ps --services --filter status=running" in call
        )
        up_index = next(i for i, call in enumerate(call_list) if "up -d" in call)
        assert ps_index < up_index, "Should call ps before up"


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
