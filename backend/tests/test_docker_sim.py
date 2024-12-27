# test_docker_simulation.py
import json
import os
import subprocess

# Setup Python path
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
from docker.config import CONTAINERS
from docker.containers import ensure_containers_running, stop_containers
from docker.scripts.docker_simulation import (
    SIMULATION_RESULTS_SCHEMA,
    SimulationContainerError,
    run_docker_simulation,
    validate_docker_results,
)
from tests.database_setup import setup_test_db

os.environ["TESTING"] = "1"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    setup_test_db()


@pytest.fixture(scope="module")
def db_session():
    engine = get_db_engine()
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture(scope="module")
def client(db_session):
    def get_db_session_override():
        return db_session

    app.dependency_overrides[get_db_engine] = get_db_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def admin_token(client):
    admin_login_response = client.post(
        "/admin_login", json={"username": "Administrator", "password": "BOSSMAN"}
    )
    assert admin_login_response.status_code == 200
    return admin_login_response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_greedy_pig_docker_simulation(client, admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response.status_code == 200
    response_data = simulation_response.json()
    assert "data" in response_data
    assert "total_points" in response_data["data"]
    assert "feedback" in response_data["data"]


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


@patch("subprocess.run")
def test_ensure_containers_running_success(mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = ""
    mock_subprocess_run.return_value.returncode = 0

    # Mock inspect result
    mock_inspect_result = mock_subprocess_run.return_value
    mock_inspect_result.stdout = json.dumps([{"State": {"Running": True}}])

    ensure_containers_running("/test/root/dir")

    # Verify container checks and creation calls
    assert mock_subprocess_run.call_count >= len(CONTAINERS) * 2


@patch("subprocess.run")
def test_ensure_containers_running_failure(mock_subprocess_run):
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        1, "docker build", "Build failed"
    )

    with pytest.raises(RuntimeError) as exc_info:
        ensure_containers_running("/test/root/dir")

    assert "Failed to manage" in str(exc_info.value)


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
