import json
import os
import subprocess
import time
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from backend.docker_utils.compose_utils import (
    check_service_health,
    ensure_services_running,
    get_container_logs,
    stop_services,
)


@pytest.fixture
def mock_docker_run():
    """Mock subprocess.run for docker commands"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="container_id", stderr="")
        yield mock_run


@pytest.fixture
def mock_env_setup():
    """Setup environment variables"""
    with patch.dict(
        "os.environ", {"SERVICE_TOKEN": "test_token", "SECRET_KEY": "test_key"}
    ):
        yield


def test_docker_compose_error_recovery(mock_docker_run, mock_env_setup):
    """Test service recovery after unexpected shutdown"""
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        cmd = " ".join(args[0])

        if "ps" in cmd:
            if call_count <= 2:  # First ps command shows no services running
                return Mock(returncode=0, stdout="", stderr="")
            return Mock(returncode=0, stdout="validator\nsimulator\n", stderr="")

        if "config" in cmd:
            return Mock(returncode=0, stdout="validator\nsimulator\n", stderr="")

        return Mock(returncode=0, stdout="container_id", stderr="")

    mock_docker_run.side_effect = side_effect

    result = ensure_services_running()
    assert result is True

    # Should have tried to start services since they weren't running initially
    assert any(
        ("up" in " ".join(call[0][0])) for call in mock_docker_run.call_args_list
    )


def test_container_logs_retrieval_failure(mock_docker_run):
    """Test behavior when log retrieval fails"""
    mock_docker_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=["docker-compose", "logs", "validator"],
        output=b"No such service: validator",
    )

    logs = get_container_logs("validator")
    assert "Could not retrieve logs" in logs


def test_multiple_service_operations(mock_docker_run, mock_env_setup):
    """Test behavior when managing multiple services simultaneously"""
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        cmd = " ".join(args[0])

        if "ps" in cmd:
            if "validator" in cmd:  # Check for specific service
                return Mock(returncode=0, stdout="validator  Up", stderr="")
            elif "simulator" in cmd:
                # Simulator is down on first check, then up on second
                return Mock(
                    returncode=0,
                    stdout="" if call_count < 3 else "simulator  Up",
                    stderr="",
                )
            else:  # Check for all services
                if call_count < 3:  # First check shows only validator running
                    return Mock(returncode=0, stdout="validator\n", stderr="")
                return Mock(returncode=0, stdout="validator\nsimulator\n", stderr="")

        if "config" in cmd:
            return Mock(returncode=0, stdout="validator\nsimulator\n", stderr="")

        return Mock(returncode=0, stdout="container_id", stderr="")

    mock_docker_run.side_effect = side_effect

    result = ensure_services_running()
    assert result is True


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    def json(self):
        return {"status": "healthy"}


def test_service_health_check(monkeypatch):
    """Test health check for services"""
    with patch("subprocess.run") as mock_run:
        # Set different return values based on command arguments
        def side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if isinstance(cmd, list) and "ps" in cmd:
                return Mock(returncode=0, stdout="validator  Up", stderr="")
            elif "inspect" in str(cmd):
                return Mock(returncode=0, stdout="healthy", stderr="")
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        # Call the function
        is_healthy, message = check_service_health("validator")

        # Verify result
        assert is_healthy is True


def test_service_health_check_failure(monkeypatch):
    """Test health check failure for services"""

    with patch("subprocess.run") as mock_run:
        # Mock ps command showing service is not running
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # Call the function
        is_healthy, message = check_service_health("validator")

        # Verify result
        assert is_healthy is False
        assert "not running" in message.lower()


def test_service_environment_validation(mock_docker_run):
    """Test service environment variable validation"""

    def side_effect(*args, **kwargs):
        # First call - ps shows no services
        if "ps" in " ".join(args[0]):
            return Mock(returncode=0, stdout="", stderr="")

        # Second call - config shows required services
        if "config" in " ".join(args[0]):
            return Mock(returncode=0, stdout="validator\nsimulator\n", stderr="")

        # Third call - up fails due to missing env vars
        if "up" in " ".join(args[0]) and (
            "SERVICE_TOKEN" not in os.environ or "SECRET_KEY" not in os.environ
        ):
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=args[0],
                output=b"Error: environment variables missing",
            )

        return Mock(returncode=0, stdout="container_id", stderr="")

    mock_docker_run.side_effect = side_effect

    # Test missing environment variables
    with patch.dict("os.environ", clear=True):
        result = ensure_services_running()
        assert result is False  # Should fail due to missing env vars

    # Test with environment variables
    with patch.dict(
        "os.environ", {"SERVICE_TOKEN": "test_token", "SECRET_KEY": "test_key"}
    ):
        # Replace side effect to allow success
        mock_docker_run.side_effect = lambda *args, **kwargs: Mock(
            returncode=0, stdout="container_id", stderr=""
        )
        result = ensure_services_running()
        assert result is True  # Should succeed with env vars
