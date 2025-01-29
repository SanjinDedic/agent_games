import logging
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.database.db_models import League
from backend.docker_utils.services.simulation_server import (
    aggregate_simulation_results,
    app,
)


@pytest.fixture
def simulator_client() -> TestClient:
    """Create a test client for the simulator service"""
    return TestClient(app, base_url="http://localhost:8002")


@pytest.fixture
def test_league(db_session: Session) -> League:
    """Create a test league for simulations"""
    league = League(
        id=1,  # Explicitly set ID for test
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="prisoners_dilemma",
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    return league


def test_health_check_success(simulator_client: TestClient):
    """Test successful health check endpoint response"""
    response = simulator_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_simulate_endpoint_success(simulator_client: TestClient, test_league: League):
    """Test successful simulation scenarios"""

    # Test case 1: Basic simulation request with minimal fields
    data = {
        "league_id": test_league.id,
        "game_name": "prisoners_dilemma",
        "num_simulations": 100,
        "player_feedback": False,
        "custom_rewards": None,
    }
    response = simulator_client.post("/simulate", json=data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "simulation_results" in data

    # Test case 2: Simulation with custom rewards
    data = {
        "league_id": test_league.id,
        "game_name": "prisoners_dilemma",
        "num_simulations": 100,
        "custom_rewards": [4, 0, 6, 2],
        "player_feedback": False,
    }
    response = simulator_client.post("/simulate", json=data)
    assert response.status_code == 200
    data = response.json()
    assert "simulation_results" in data

    # Test case 3: Simulation with player feedback
    data = {
        "league_id": test_league.id,
        "game_name": "prisoners_dilemma",
        "num_simulations": 100,
        "player_feedback": True,
        "custom_rewards": None,
    }
    response = simulator_client.post("/simulate", json=data)
    assert response.status_code == 200
    data = response.json()
    assert "feedback" in data
    assert "player_feedback" in data


def test_simulate_endpoint_exceptions(
    simulator_client: TestClient, test_league: League
):
    """Test error cases for simulation endpoint"""

    # Test case 1: Invalid league ID
    data = {
        "league_id": 99999,  # Non-existent league
        "game_name": "prisoners_dilemma",
        "num_simulations": 100,
        "player_feedback": False,
        "custom_rewards": None,
    }
    response = simulator_client.post("/simulate", json=data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "League not found" in data["message"]

    # Test case 2: Invalid game name
    data = {
        "league_id": test_league.id,
        "game_name": "invalid_game",
        "num_simulations": 100,
        "player_feedback": False,
        "custom_rewards": None,
    }
    response = simulator_client.post("/simulate", json=data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "Unknown game" in data["message"]

    # Test case 3: Negative number of simulations
    data = {
        "league_id": test_league.id,
        "game_name": "prisoners_dilemma",
        "num_simulations": -1,
        "player_feedback": False,
        "custom_rewards": None,
    }
    response = simulator_client.post("/simulate", json=data)
    assert response.status_code == 422  # Validation error
    data = response.json()
    assert "detail" in data
    assert "Number of simulations must be between 1 and 10000" in str(data["detail"])

    # Test case 4: Too many simulations
    data = {
        "league_id": test_league.id,
        "game_name": "prisoners_dilemma",
        "num_simulations": 20000,
        "player_feedback": False,
        "custom_rewards": None,
    }
    response = simulator_client.post("/simulate", json=data)
    assert response.status_code == 422  # Validation error
    data = response.json()
    assert "detail" in data
    assert "Number of simulations must be between 1 and 10000" in str(data["detail"])


def test_get_logs_success(simulator_client: TestClient):
    """Test successful log retrieval"""
    response = simulator_client.get("/logs")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data


def test_aggregate_simulation_results_success():
    """Test successful aggregation of simulation results"""
    simulation_results = [
        {
            "points": {"player1": 10, "player2": 20},
            "table": {"wins": {"player1": 1, "player2": 2}},
        },
        {
            "points": {"player1": 15, "player2": 25},
            "table": {"wins": {"player1": 2, "player2": 3}},
        },
    ]

    result = aggregate_simulation_results(simulation_results, 2)
    assert result["total_points"] == {"player1": 25, "player2": 45}
    assert result["num_simulations"] == 2
    assert "table" in result
