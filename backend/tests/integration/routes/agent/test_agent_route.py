# tests/routes/agent/test_agent_router.py

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.database.db_models import AgentAPIKey, League, Team, TeamType
from backend.routes.agent import agent_db
from backend.routes.auth.auth_core import create_access_token
from backend.tests.conftest import add_submission

from unittest.mock import patch
from backend.time_utils import utc_now


@pytest.fixture(autouse=True)
def clear_simulation_rate_keys():
    """Reset the valkey rate-limit counters between tests.

    Team ids restart with each test's TRUNCATE, so without this a counter
    left by an earlier test (or an earlier suite run inside the 60s window)
    would bleed into the next test's budget.
    """
    redis = agent_db._get_redis()
    for key in redis.scan_iter("agent-sim-rate:*"):
        redis.delete(key)


@pytest.fixture
def setup_agent_league(db_session: Session) -> League:
    """Create a test league for agent testing"""
    league = League(
        name="agent_test_league",
        game="lineup4",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
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
        add_submission(
            db_session,
            team_id=team.id,
            code=lineup4_code,
            timestamp=utc_now(),
        )

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
            "team_id": setup_agent_team.id,
        },
        expires_delta=timedelta(minutes=30),
    )


def test_agent_simulation_success(
    client: TestClient,
    db_session: Session,
    setup_agent_league: League,
    setup_agent_team: Team,
    setup_player_teams_with_submissions,
    agent_token: str,
):
    """Test successful simulation scenarios for agent endpoints"""

    headers = {"Authorization": f"Bearer {agent_token}"}

    # Test case 1: Basic simulation request
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
    assert data["status"] == "success"
    assert "data" in data
    assert "simulation_results" in data["data"]

    # Test case 2: Simulation with custom rewards
    response = client.post(
        "/agent/simulate",
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
    response = client.post(
        "/agent/simulate",
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
    assert "access_token" in response.json()

    # Test case 2: Invalid API key
    response = client.post("/auth/agent-login", json={"api_key": "invalid_key"})
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()

    # Test case 3: Inactive API key
    setup_api_key.is_active = False
    db_session.add(setup_api_key)
    db_session.commit()

    response = client.post("/auth/agent-login", json={"api_key": setup_api_key.key})
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_agent_rate_limiting(
    client: TestClient,
    db_session: Session,
    setup_agent_league: League,
    agent_token: str,
    monkeypatch,
):
    """Requests within the per-minute limit succeed; the next one is
    rejected with a rate-limit error. The limit is dropped to 3 so the
    rejected branch is reached without ten real simulation runs."""

    monkeypatch.setattr(agent_db, "SIMULATIONS_PER_MINUTE", 3)

    headers = {"Authorization": f"Bearer {agent_token}"}
    payload = {
        "league_id": setup_agent_league.id,
        "game_name": "lineup4",
        "num_simulations": 1,
    }

    for _ in range(3):
        response = client.post("/agent/simulate", headers=headers, json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    response = client.post("/agent/simulate", headers=headers, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "rate limit" in data["message"].lower()
