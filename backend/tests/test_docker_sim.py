import json
import os
import subprocess
import sys
from unittest.mock import mock_open, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from docker_simulation import (SIMULATION_RESULTS_SCHEMA,
                               run_docker_simulation, validate_docker_results)
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
    admin_login_response = client.post("/admin_login", json={"username": "Administrator", "password": "BOSSMAN"})
    assert admin_login_response.status_code == 200
    return admin_login_response.json()["data"]["access_token"]

def test_greedy_pig_docker_simulation(client, admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200
    response_data = simulation_response.json()
    print("here is the response data", response_data)
    assert "data" in response_data
    assert "total_points" in response_data["data"]
    assert "feedback" in response_data["data"]

@patch('subprocess.run')
def test_run_docker_simulation_success(mock_subprocess_run):
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stdout = "Docker simulation output"
    
    mock_results = {
        "feedback": "Test feedback",
        "simulation_results": {
            "total_points": {"player1": 100, "player2": 200},
            "num_simulations": 100,
            "table": {"wins": {"player1": 40, "player2": 60}}
        }
    }
    
    with patch('builtins.open', mock_open(read_data=json.dumps(mock_results))):
        success, results = run_docker_simulation("test_league", "test_game", "test_folder", None)
    
    assert success == True
    assert results == mock_results

@patch('subprocess.run')
def test_run_docker_simulation_timeout(mock_subprocess_run):
    mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=1)
    
    success, error_message = run_docker_simulation("test_league", "test_game", "test_folder", None)
    
    assert success == False
    assert "Timeout occurred" in error_message

@patch('subprocess.run')
def test_run_docker_simulation_subprocess_error(mock_subprocess_run):
    mock_subprocess_run.return_value.returncode = 1
    mock_subprocess_run.return_value.stderr = "Subprocess error"
    
    success, error_message = run_docker_simulation("test_league", "test_game", "test_folder", None)
    
    assert success == False
    assert "An error occurred while running the docker container" in error_message

@patch('subprocess.run')
def test_run_docker_simulation_json_error(mock_subprocess_run):
    mock_subprocess_run.return_value.returncode = 0
    
    with patch('builtins.open', mock_open(read_data="Invalid JSON")):
        success, error_message = run_docker_simulation("test_league", "test_game", "test_folder", None)
    
    assert success == False
    assert "An error occurred while parsing the simulation results" in error_message

@patch('subprocess.run')
def test_run_docker_simulation_file_not_found(mock_subprocess_run):
    mock_subprocess_run.return_value.returncode = 0
    
    with patch('builtins.open', side_effect=FileNotFoundError):
        success, error_message = run_docker_simulation("test_league", "test_game", "test_folder", None)
    
    assert success == False
    assert "Docker results file not found" in error_message

@patch('subprocess.run')
def test_run_docker_simulation_invalid_results(mock_subprocess_run):
    mock_subprocess_run.return_value.returncode = 0
    
    invalid_results = {
        "feedback": "Test feedback",
        "simulation_results": {
            "total_points": {"player1": 100, "player2": 200},
            "num_simulations": 100,
            # Missing "table" key
        }
    }
    
    with patch('builtins.open', mock_open(read_data=json.dumps(invalid_results))):
        success, error_message = run_docker_simulation("test_league", "test_game", "test_folder", None)
    
    assert success == False
    assert "Invalid results format" in error_message

def test_validate_docker_results():
    valid_results = {
        "feedback": "Test feedback",
        "simulation_results": {
            "total_points": {"player1": 100, "player2": 200},
            "num_simulations": 100,
            "table": {"wins": {"player1": 40, "player2": 60}}
        }
    }
    assert validate_docker_results(valid_results) == True

    invalid_results = {
        "feedback": "Test feedback",
        "simulation_results": {
            "total_points": {"player1": 100, "player2": 200},
            "num_simulations": 100,
            # Missing "table" key
        }
    }
    assert validate_docker_results(invalid_results) == False

def test_simulation_results_schema():
    assert "feedback" in SIMULATION_RESULTS_SCHEMA["properties"]
    assert "simulation_results" in SIMULATION_RESULTS_SCHEMA["properties"]
    assert "total_points" in SIMULATION_RESULTS_SCHEMA["properties"]["simulation_results"]["properties"]
    assert "num_simulations" in SIMULATION_RESULTS_SCHEMA["properties"]["simulation_results"]["properties"]
    assert "table" in SIMULATION_RESULTS_SCHEMA["properties"]["simulation_results"]["properties"]

if __name__ == "__main__":
    pytest.main()