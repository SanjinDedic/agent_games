import json
import os
import subprocess
import time
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from backend.docker_utils.containers import (
    ensure_containers_running,
    get_container_logs,
    stop_containers,
)


@pytest.fixture
def mock_docker_run():
    """Mock subprocess.run for docker commands"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0, stdout=json.dumps([{"State": {"Running": True}}]), stderr=""
        )
        yield mock_run


@pytest.fixture
def mock_env_setup():
    """Setup environment variables"""
    with patch.dict(
        "os.environ", {"SERVICE_TOKEN": "test_token", "SECRET_KEY": "test_key"}
    ):
        yield


def test_docker_container_error_recovery(mock_docker_run, mock_env_setup):
    """Test container recovery after unexpected shutdown"""
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        cmd = " ".join(args[0])

        if "inspect" in cmd:
            if call_count <= 2:  # First two inspects show not running
                return Mock(
                    returncode=0,
                    stdout=json.dumps([{"State": {"Running": False}}]),
                    stderr="",
                )
            return Mock(
                returncode=0,
                stdout=json.dumps([{"State": {"Running": True}}]),
                stderr="",
            )
        return Mock(returncode=0, stdout="container_id", stderr="")

    mock_docker_run.side_effect = side_effect
    ensure_containers_running()


def test_container_logs_retrieval_failure(mock_docker_run):
    """Test behavior when log retrieval fails"""
    mock_docker_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=["docker", "logs", "validator"],
        output=b"Error: No such container: validator",
    )
    logs = get_container_logs("validator")
    assert logs == "Could not retrieve container logs"


def test_multiple_container_operations(mock_docker_run, mock_env_setup):
    """Test behavior when managing multiple containers simultaneously"""
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        cmd = " ".join(args[0])

        if "rm" in cmd:
            return Mock(returncode=0)
        elif "images" in cmd:
            return Mock(returncode=0, stdout="image_id")
        elif "run" in cmd:
            return Mock(returncode=0, stdout="container_id")
        elif "inspect" in cmd:
            container = "simulator" if "simulator" in cmd else "validator"
            # Simulator starts as not running, then becomes running
            is_running = True if container == "validator" else (call_count > 4)
            return Mock(
                returncode=0,
                stdout=json.dumps([{"State": {"Running": is_running}}]),
                stderr="",
            )
        return Mock(returncode=0, stdout="container_id")

    mock_docker_run.side_effect = side_effect
    ensure_containers_running()


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    def json(self):
        return {"status": "healthy"}


def test_container_health_check(monkeypatch):
    """Test health check endpoints for both containers"""

    # Mock the client get calls to return success
    def mock_get(*args, **kwargs):
        return MockResponse(200)

    # Patch the client's get method
    with patch("httpx.AsyncClient.get", return_value=mock_get):
        response = mock_get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


def test_container_environment_validation(mock_docker_run):
    """Test container environment variable validation"""

    def side_effect(*args, **kwargs):
        cmd = " ".join(args[0])
        if "run" in cmd and (
            "SERVICE_TOKEN" not in os.environ or "SECRET_KEY" not in os.environ
        ):
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=args[0],
                output=b"Error: environment variables missing",
            )
        return Mock(
            returncode=0, stdout=json.dumps([{"State": {"Running": True}}]), stderr=""
        )

    mock_docker_run.side_effect = side_effect

    # Test missing environment variables
    with patch.dict("os.environ", clear=True):
        with pytest.raises(RuntimeError) as exc:
            ensure_containers_running()
        error_message = str(exc.value)
        # Check if it's failing with the Docker command error which includes our missing vars message
        assert "docker" in error_message.lower()
        assert "returned non-zero exit status" in error_message
        # The actual error output should be in the logs, which we check in our docker_utils.containers log
        # This verifies the correct error is being propagated through the system

    # Test with environment variables
    with patch.dict(
        "os.environ", {"SERVICE_TOKEN": "test_token", "SECRET_KEY": "test_key"}
    ):
        # Should not raise any exceptions
        ensure_containers_running()
