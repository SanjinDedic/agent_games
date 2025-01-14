import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import mock_open, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Now import project modules
from api import app
from database import get_db_engine
from docker_utils.config import CONTAINERS
from docker_utils.containers import ensure_containers_running, stop_containers
from docker_utils.scripts.docker_simulation import (
    SIMULATION_RESULTS_SCHEMA,
    SimulationContainerError,
    run_docker_simulation,
    validate_docker_results,
)


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
                response = await client.get("http://localhost:8002/")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
        except httpx.RequestError as e:
            pytest.fail(
                f"Simulator container is not running or not accessible: {str(e)}"
            )

    asyncio.run(check_health())


@pytest.mark.asyncio
async def test_simulator_container_health():
    """Verify the simulator container is running and healthy"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8002/")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    except httpx.RequestError as e:
        pytest.fail(f"Simulator container is not running or not accessible: {str(e)}")


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_run_docker_simulation_success(mock_post):
    mock_response = type(
        "Response",
        (),
        {
            "status_code": 200,
            "json": lambda: {
                "feedback": "Test feedback",
                "simulation_results": {
                    "total_points": {"player1": 100, "player2": 200},
                    "num_simulations": 100,
                    "table": {"wins": {"player1": 40, "player2": 60}},
                },
            },
        },
    )
    mock_post.return_value = mock_response

    success, results = await run_docker_simulation(
        "test_league", "test_game", "test_folder", None
    )

    assert success is True
    assert results["feedback"] == "Test feedback"
    assert "total_points" in results["simulation_results"]


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_run_docker_simulation_timeout(mock_post):
    mock_post.side_effect = httpx.TimeoutException("Timeout")

    success, error_message = await run_docker_simulation(
        "test_league", "test_game", "test_folder", None
    )

    assert success is False
    assert "Failed to connect to simulation service" in error_message


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_run_docker_simulation_api_error(mock_post):
    mock_response = type(
        "Response", (), {"status_code": 500, "text": "Internal server error"}
    )
    mock_post.return_value = mock_response

    success, error_message = await run_docker_simulation(
        "test_league", "test_game", "test_folder", None
    )

    assert success is False
    assert "Simulation failed with status code 500" in error_message


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


def test_validate_docker_results():
    valid_results = {
        "feedback": "Test feedback",
        "simulation_results": {
            "total_points": {"player1": 100, "player2": 200},
            "num_simulations": 100,
            "table": {"wins": {"player1": 40, "player2": 60}},
        },
    }
    assert validate_docker_results(valid_results) is True

    invalid_results = {
        "feedback": "Test feedback",
        "simulation_results": {
            "total_points": {"player1": 100, "player2": 200},
            "num_simulations": 100,
            # Missing "table" key
        },
    }
    assert validate_docker_results(invalid_results) is False


def test_simulation_results_schema():
    assert "feedback" in SIMULATION_RESULTS_SCHEMA["properties"]
    assert "simulation_results" in SIMULATION_RESULTS_SCHEMA["properties"]
    assert (
        "total_points"
        in SIMULATION_RESULTS_SCHEMA["properties"]["simulation_results"]["properties"]
    )
    assert (
        "num_simulations"
        in SIMULATION_RESULTS_SCHEMA["properties"]["simulation_results"]["properties"]
    )
    assert (
        "table"
        in SIMULATION_RESULTS_SCHEMA["properties"]["simulation_results"]["properties"]
    )


if __name__ == "__main__":
    pytest.main(["-v"])
