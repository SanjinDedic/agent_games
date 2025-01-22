import json
import subprocess
from unittest.mock import patch

import httpx
import pytest

from backend.docker_utils.config import CONTAINERS
from backend.docker_utils.containers import ensure_containers_running, stop_containers


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


# Does this need to be mocked??
@patch("subprocess.run")
def test_ensure_containers_running_success(mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = ""
    mock_subprocess_run.return_value.returncode = 0

    # Mock inspect result
    mock_inspect_result = mock_subprocess_run.return_value
    mock_inspect_result.stdout = json.dumps([{"State": {"Running": True}}])

    ensure_containers_running()

    # Verify container checks and creation calls
    assert mock_subprocess_run.call_count >= len(CONTAINERS) * 2


@patch("subprocess.run")
def test_ensure_containers_running_failure(mock_subprocess_run):
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        1, "docker build", "Build failed"
    )

    with pytest.raises(RuntimeError) as exc_info:
        ensure_containers_running()

    assert "Failed to manage" in str(exc_info.value)


# Can this be done without mocking?
@patch("subprocess.run")
def test_stop_containers(mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = "container-id"
    mock_subprocess_run.return_value.returncode = 0

    stop_containers()

    # Verify stop and remove calls for each container
    expected_calls = len(CONTAINERS) * 3  # check + stop + remove for each container
    assert mock_subprocess_run.call_count == expected_calls


if __name__ == "__main__":
    pytest.main(["-v"])
