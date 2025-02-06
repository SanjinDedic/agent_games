from datetime import datetime, timedelta

import httpx
import pytest
from sqlmodel import Session

from backend.database.db_models import League, Submission, Team
from backend.games.base_game import BaseGame

# Mark all tests to use containers
pytestmark = pytest.mark.usefixtures("ensure_containers")


@pytest.fixture
def test_league(db_session):
    """Create a test league for testing"""
    league = League(
        name="test_league",
        game="prisoners_dilemma",  # Use real game type
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=1),
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    return league


@pytest.fixture
def test_submission(db_session, test_league, client, auth_headers):
    """Create a submission through the API"""
    # First create a team
    team_response = client.post(
        "/admin/team-create",
        headers=auth_headers,
        json={
            "name": "test_team",
            "password": "test_pass",
            "school_name": "Test School",
        },
    )
    assert team_response.status_code == 200

    # Assign team to league
    assign_response = client.post(
        "/admin/league-assign", headers=auth_headers, json={"name": test_league.name}
    )
    assert assign_response.status_code == 200

    # Submit code
    code = """
from backend.games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
"""

    submit_response = client.post(
        "/user/submit-agent", headers=auth_headers, json={"code": code}
    )
    assert submit_response.status_code == 200
    return submit_response.json()


@pytest.mark.asyncio
async def xtest_validation_workflow(db_session, test_league, test_submission):
    """Test base game usage in validation workflow"""
    async with httpx.AsyncClient() as client:
        # Request validation through validator service
        response = await client.post(
            "http://localhost:8001/validate",
            json={
                "code": test_submission["code"],
                "game_name": test_league.game,
                "team_name": "test_team",
                "num_simulations": 10,
            },
            timeout=30.0,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "simulation_results" in data


@pytest.mark.asyncio
async def xtest_simulation_workflow(db_session, test_league, test_submission):
    """Test base game usage in simulation workflow"""
    async with httpx.AsyncClient() as client:
        # Run simulation through simulator service
        response = await client.post(
            "http://localhost:8002/simulate",
            json={
                "league_id": test_league.id,
                "game_name": test_league.game,
                "num_simulations": 10,
            },
            timeout=30.0,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "simulation_results" in data
        assert data["simulation_results"]["total_points"]


@pytest.mark.asyncio
async def test_error_handling(db_session, test_league):
    """Test error handling in validator/simulator services"""
    async with httpx.AsyncClient() as client:
        # Test invalid code handling
        invalid_code = """
            This is not valid Python code
        """
        response = await client.post(
            "http://localhost:8001/validate",
            json={
                "code": invalid_code,
                "game_name": test_league.game,
                "team_name": "test_team",
                "num_simulations": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "syntax error" in data["message"].lower()


@pytest.mark.asyncio
async def xtest_concurrent_simulations(db_session, test_league, test_submission):
    """Test handling multiple simultaneous simulations"""
    async with httpx.AsyncClient() as client:
        # Create multiple simulation tasks
        tasks = []
        for _ in range(3):
            task = client.post(
                "http://localhost:8002/simulate",
                json={
                    "league_id": test_league.id,
                    "game_name": test_league.game,
                    "num_simulations": 10,
                },
            )
            tasks.append(task)

        # Run concurrently
        import asyncio

        responses = await asyncio.gather(*tasks)

        # Verify all succeeded
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"


def test_base_game_initialization(test_league):
    """Test basic initialization of BaseGame"""
    game = BaseGame(test_league)
    assert game.verbose is False
    assert game.league == test_league
    assert isinstance(game.players, list)
    assert isinstance(game.scores, dict)
