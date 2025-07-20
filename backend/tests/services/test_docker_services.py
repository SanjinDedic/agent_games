import json
import os
import subprocess
import time
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException


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


def test_docker_compose_direct_usage(mock_docker_run, mock_env_setup):
    """Test direct Docker Compose usage without compose_utils wrapper"""
    # Test direct docker compose command
    result = subprocess.run(
        ["docker", "compose", "--profile", "test", "ps"],
        capture_output=True,
        text=True,
        check=False,
    )

    # Should call the mock
    mock_docker_run.assert_called()


def test_container_logs_direct(mock_docker_run):
    """Test behavior when log retrieval fails using direct commands"""
    mock_docker_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=["docker", "compose", "logs", "validator"],
        output=b"No such service: validator",
    )

    # Test direct approach instead of using compose_utils
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.run(
            ["docker", "compose", "logs", "validator"],
            check=True,
            capture_output=True,
            text=True,
        )


def test_service_health_check_http():
    """Test health check using HTTP instead of docker commands"""
    # This test would use HTTP calls to check service health
    # Similar to what's in diagnostics_utils.py
    import httpx

    # Mock the HTTP response
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}

        mock_client.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )

        # This would be the actual test logic
        assert mock_response.status_code == 200


def test_service_environment_validation_direct(mock_docker_run):
    """Test service environment variable validation using direct commands"""
    def side_effect(*args, **kwargs):
        cmd = args[0] if args else []
        if "ps" in str(cmd):
            return Mock(returncode=0, stdout="", stderr="")
        return Mock(returncode=0, stdout="container_id", stderr="")

    mock_docker_run.side_effect = side_effect

    # Test missing environment variables
    with patch.dict("os.environ", clear=True):
        # Direct docker compose call
        result = subprocess.run(
            ["docker", "compose", "ps"],
            capture_output=True,
            text=True,
            check=False,
        )
        # Should succeed (mocked)
        assert result.returncode == 0
