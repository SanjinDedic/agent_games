# tests/routes/agent/test_agent_router.py

from datetime import datetime, timedelta
import httpx

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.database.db_models import AgentAPIKey, League, Team, TeamType, Submission
from backend.routes.auth.auth_core import create_access_token
from backend.tests.conftest import inspect_db_state, ensure_containers

# import patch
from unittest.mock import patch

@pytest.fixture
def setup_agent_league(db_session: Session) -> League:
    """Create a test league for agent testing"""
    league = League(
        name="agent_test_league",
        game="lineup4",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        league_type="agent",
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    return league


@pytest.fixture
def setup_agent_team(db_session: Session, setup_agent_league: League) -> Team:
    """Create a test agent team"""
    team = Team(
        name="test_agent",
        school_name="AI Lab Test",
        league_id=setup_agent_league.id,
        team_type=TeamType.AGENT,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


@pytest.fixture
def setup_player_teams_with_submissions(
    db_session: Session, setup_agent_league: League
):
    """Create player teams with submissions for the agent to simulate against"""
    # Create a few player teams
    player_teams = []
    for i in range(3):
        team = Team(
            name=f"player_team_{i+1}",
            school_name=f"Test School {i+1}",
            league_id=setup_agent_league.id,
            team_type=TeamType.STUDENT,
            password_hash="dummy_hash",
        )
        db_session.add(team)
        player_teams.append(team)

    db_session.commit()

    # Create submissions for each player team
    lineup4_code = '''
def make_move(my_history, opponent_history, my_score, opponent_score):
    """Simple lineup4 strategy"""
    if len(my_history) == 0:
        return 1
    return (my_history[-1] % 4) + 1
'''

    for team in player_teams:
        db_session.refresh(team)
        submission = Submission(
            team_id=team.id,
            code=lineup4_code,
            submission_time=datetime.now(),
            is_valid=True,
        )
        db_session.add(submission)

    db_session.commit()
    return player_teams


@pytest.fixture
def setup_api_key(db_session: Session, setup_agent_team: Team) -> AgentAPIKey:
    """Create an API key for the test agent"""
    api_key = AgentAPIKey(
        key="test_api_key_12345", team_id=setup_agent_team.id, is_active=True
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)
    return api_key


@pytest.fixture
def agent_token(setup_agent_team: Team) -> str:
    """Create a valid agent token"""
    return create_access_token(
        data={
            "sub": setup_agent_team.name,
            "role": "ai_agent",
            "team_name": setup_agent_team.name,
        },
        expires_delta=timedelta(minutes=30),
    )


@pytest.mark.asyncio
async def test_agent_simulation_success(
    db_session: Session,
    setup_agent_league: League,
    setup_agent_team: Team,
    setup_player_teams_with_submissions,  # Add this fixture
    agent_token: str,
    ensure_containers,  # Add as fixture parameter
):
    """Test successful simulation scenarios for agent endpoints"""

    headers = {"Authorization": f"Bearer {agent_token}"}

    async with httpx.AsyncClient() as client:
        # Test case 1: Basic simulation request
        response = await client.post(
            "http://localhost:8000/agent/simulate",
            headers=headers,
            json={
                "league_id": setup_agent_league.id,
                "game_name": "lineup4",
                "num_simulations": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        print("Should work this ", data)
        assert data["status"] == "success"
        assert "data" in data
        assert "simulation_results" in data["data"]

        # Test case 2: Simulation with custom rewards
        response = await client.post(
            "http://localhost:8000/agent/simulate",
            headers=headers,
            json={
                "league_id": setup_agent_league.id,
                "game_name": "lineup4",
                "num_simulations": 10,
                "custom_rewards": [10, 5, 0],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data

        # Test case 3: Simulation with player feedback
        response = await client.post(
            "http://localhost:8000/agent/simulate",
            headers=headers,
            json={
                "league_id": setup_agent_league.id,
                "game_name": "lineup4",
                "num_simulations": 10,
                "player_feedback": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        print("Player feedback simulation responseXXX: ", data)
        assert data["status"] == "success"
        assert "data" in data


def test_agent_simulation_exceptions(
    client: TestClient,
    db_session: Session,
    setup_agent_league: League,
    agent_token: str,
):
    """Test error cases for agent simulation endpoint"""

    headers = {"Authorization": f"Bearer {agent_token}"}

    # Test case 1: Invalid league ID
    response = client.post(
        "/agent/simulate",
        headers=headers,
        json={"league_id": 99999, "game_name": "lineup4", "num_simulations": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()

    # Test case 2: Invalid game name
    response = client.post(
        "/agent/simulate",
        headers=headers,
        json={
            "league_id": setup_agent_league.id,
            "game_name": "invalid_game",
            "num_simulations": 10,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"

    # Test case 3: Invalid number of simulations
    response = client.post(
        "/agent/simulate",
        headers=headers,
        json={
            "league_id": setup_agent_league.id,
            "game_name": "lineup4",
            "num_simulations": -1,
        },
    )
    assert response.status_code == 422

    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/agent/simulate",
        json={
            "league_id": setup_agent_league.id,
            "game_name": "lineup4",
            "num_simulations": 10,
        },
    )
    assert response.status_code == 401

    # Test case 5: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "test", "role": "student"}, expires_delta=timedelta(minutes=30)
    )
    response = client.post(
        "/agent/simulate",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={
            "league_id": setup_agent_league.id,
            "game_name": "lineup4",
            "num_simulations": 10,
        },
    )
    assert response.status_code == 403


def test_agent_api_key_validation(
    client: TestClient, db_session: Session, setup_api_key: AgentAPIKey
):
    """Test API key validation scenarios"""

    # Test case 1: Valid API key login
    response = client.post("/auth/agent-login", json={"api_key": setup_api_key.key})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "access_token" in data["data"]

    # Test case 2: Invalid API key
    response = client.post("/auth/agent-login", json={"api_key": "invalid_key"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "error" in data["message"].lower()

    # Test case 3: Inactive API key
    setup_api_key.is_active = False
    db_session.add(setup_api_key)
    db_session.commit()

    response = client.post("/auth/agent-login", json={"api_key": setup_api_key.key})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "error" in data["message"].lower()


def test_agent_rate_limiting(
    client: TestClient,
    db_session: Session,
    setup_agent_league: League,
    agent_token: str,
):
    """Test rate limiting for agent simulation requests"""

    headers = {"Authorization": f"Bearer {agent_token}"}

    # Make multiple rapid requests
    for i in range(10):
        response = client.post(
            "/agent/simulate",
            headers=headers,
            json={
                "league_id": setup_agent_league.id,
                "game_name": "lineup4",
                "num_simulations": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        if i < 10:  # First 10 requests should succeed
            assert data["status"] == "success"
        else:  # 11th request should be rate limited
            assert data["status"] == "error"
            assert "rate limit" in data["message"].lower()
