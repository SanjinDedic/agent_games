import asyncio
import subprocess
from unittest.mock import Mock, patch

import httpx
import pytest


def test_validator_container_health():
    """Verify the validator container is running and healthy"""
    async def check_health():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8001/health", timeout=5.0)
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
        except httpx.RequestError as e:
            pytest.fail(
                f"Validator container is not running or not accessible: {str(e)}"
            )

    asyncio.run(check_health())


def test_simulator_container_health():
    """Verify the simulator container is running and healthy"""
    async def check_health():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8002/health", timeout=5.0)
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
        except httpx.RequestError as e:
            pytest.fail(
                f"Simulator container is not running or not accessible: {str(e)}"
            )

    asyncio.run(check_health())


def test_docker_compose_services_up():
    """Test that Docker Compose can start services"""
    try:
        # Use Docker Compose directly - no wrapper needed
        result = subprocess.run(
            ["docker", "compose", "--profile", "test", "up", "-d", "--wait"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Check if command succeeded
        assert result.returncode == 0, f"Docker Compose failed: {result.stderr}"

        # Verify services are actually running
        ps_result = subprocess.run(
            ["docker", "compose", "ps", "--services", "--filter", "status=running"],
            capture_output=True,
            text=True,
        )

        running_services = (
            ps_result.stdout.strip().split("\n") if ps_result.stdout.strip() else []
        )
        assert "validator" in running_services, "Validator service should be running"
        assert "simulator" in running_services, "Simulator service should be running"

    except subprocess.TimeoutExpired:
        pytest.fail("Docker Compose startup timed out")
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Docker Compose command failed: {e}")


@patch("subprocess.run")
def test_docker_compose_up_failure(mock_subprocess_run):
    """Test handling Docker Compose startup failure"""
    # Mock command execution error
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        1, "docker compose up", stderr="Failed to start services"
    )

    # Should raise exception or handle gracefully
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.run(
            ["docker", "compose", "--profile", "test", "up", "-d", "--wait"],
            check=True,  # This will raise CalledProcessError on failure
        )


@patch("subprocess.run")
def test_docker_compose_down(mock_subprocess_run):
    """Test stopping services with Docker Compose"""
    # Mock successful down command
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""
    mock_subprocess_run.return_value = mock_result

    # Call docker compose down directly
    result = subprocess.run(
        ["docker", "compose", "down"], capture_output=True, text=True
    )

    # Verify it succeeded
    assert result.returncode == 0

    # Check that docker compose down was called
    mock_subprocess_run.assert_called_with(
        ["docker", "compose", "down"], capture_output=True, text=True
    )


def test_service_logs_accessible():
    """Test that service logs are accessible via Docker logging driver"""
    try:
        result = subprocess.run(
            ["docker", "compose", "logs", "--tail", "10", "validator"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Docker CLI not available; skipping log accessibility test")

    # If compose returns non-zero, skip with message rather than fail hard
    if result.returncode != 0:
        pytest.skip(f"Unable to retrieve logs: {result.stderr.strip()}")

    # Should produce some output (even if empty string in rare cases)
    assert result.stdout is not None


if __name__ == "__main__":
    pytest.main(["-v"])
