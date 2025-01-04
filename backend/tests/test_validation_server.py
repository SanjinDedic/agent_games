import os
from datetime import datetime, timedelta

import pytest
from docker.services.validation_server import (
    ValidationRequest,
    ValidationResponse,
    app,
    is_code_safe,
    run_single_simulation,
)
from fastapi.testclient import TestClient

# Create test client
client = TestClient(app)

# Test data
VALID_CODE = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 'collude'
"""

UNSAFE_CODE = """
import os
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        os.system('rm -rf /')
        return 'collude'
"""

INVALID_SYNTAX_CODE = "this is not valid python code"


def test_validate_code_success():
    """Test successful code validation"""
    response = client.post(
        "/validate",
        json={
            "code": VALID_CODE,
            "game_name": "prisoners_dilemma",
            "team_name": "test_team",
            "num_simulations": 10,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert "feedback" in result
    assert "simulation_results" in result

    # Verify simulation results structure
    sim_results = result["simulation_results"]
    assert "total_points" in sim_results
    assert "num_simulations" in sim_results
    assert isinstance(sim_results["total_points"], dict)


def test_validate_unsafe_code():
    """Test rejection of unsafe code"""
    response = client.post(
        "/validate",
        json={
            "code": UNSAFE_CODE,
            "game_name": "prisoners_dilemma",
            "team_name": "test_team",
            "num_simulations": 10,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "error"
    assert "unsafe operations" in result["message"].lower()


def test_validate_invalid_game():
    """Test handling of invalid game name"""
    response = client.post(
        "/validate",
        json={
            "code": VALID_CODE,
            "game_name": "invalid_game",
            "team_name": "test_team",
            "num_simulations": 10,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "error"
    assert "game" in result["message"].lower()


def test_is_code_safe():
    """Test code safety checking function"""
    assert is_code_safe(VALID_CODE) is True
    assert is_code_safe(UNSAFE_CODE) is False


def test_run_single_simulation():
    """Test single simulation execution"""
    from games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame
    from models_db import League

    league = League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=1),
        folder="leagues/test_league",
        game="prisoners_dilemma",
    )

    result = run_single_simulation(PrisonersDilemmaGame, league)
    assert result is not None
    assert "points" in result
    assert isinstance(result["points"], dict)


@pytest.mark.asyncio
async def test_validate_code_error_handling():
    """Test handling of invalid code syntax"""
    response = client.post(
        "/validate",
        json={
            "code": INVALID_SYNTAX_CODE,
            "game_name": "prisoners_dilemma",
            "team_name": "test_team",
            "num_simulations": 10,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "error"
    assert "error" in result["message"].lower()


def test_validation_request_model():
    """Test validation request model validation"""
    request = ValidationRequest(
        code=VALID_CODE,
        game_name="prisoners_dilemma",
        team_name="test_team",
        num_simulations=10,
    )
    assert request.code == VALID_CODE
    assert request.game_name == "prisoners_dilemma"
    assert request.num_simulations == 10


def test_validation_response_model():
    """Test validation response model validation"""
    response = ValidationResponse(
        status="success",
        feedback={"test": "feedback"},
        simulation_results={"points": {}},
    )
    assert response.status == "success"
    assert response.feedback == {"test": "feedback"}
    assert response.simulation_results == {"points": {}}
