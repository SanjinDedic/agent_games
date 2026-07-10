from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import League, SimulationResult, Team
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def setup_test_league(db_session: Session) -> League:
    """Create a test league with simulation results"""
    league = League(
        name="game_test_league",
        game="prisoners_dilemma",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    return league


@pytest.fixture
def setup_teams(db_session: Session, setup_test_league: League) -> list[Team]:
    """Create test teams for simulation results"""
    teams = []
    for i in range(3):
        team = Team(
            name=f"game_test_team_{i}",
            school_name=f"Test School {i}",
            password_hash="test_hash",
            league_id=setup_test_league.id,
        )
        db_session.add(team)
        teams.append(team)
    db_session.commit()
    for team in teams:
        db_session.refresh(team)
    return teams


@pytest.fixture
def setup_simulation_results(
    db_session: Session, setup_test_league: League, setup_teams: list[Team]
) -> None:
    """Create test simulation results with both markdown and JSON feedback"""

    # Create simulation with markdown feedback
    sim1 = SimulationResult(
        league_id=setup_test_league.id,
        timestamp=utc_now(),
        num_simulations=100,
        custom_rewards="[10, 8, 6, 4, 2]",
        feedback_str="# Test Results\n\n- Great performance by team 1\n- Team 2 needs improvement",
        published=True,
    )
    db_session.add(sim1)

    # Create simulation with JSON feedback
    sim2 = SimulationResult(
        league_id=setup_test_league.id,
        timestamp=utc_now() + timedelta(hours=1),
        num_simulations=100,
        custom_rewards="[10, 8, 6, 4, 2]",
        feedback_json='{"analysis": {"top_team": "Team 1", "improvements": ["Team 2 strategy", "Team 3 consistency"]}}',
        published=False,
    )
    db_session.add(sim2)
    db_session.commit()


def test_get_game_instructions_success(client):
    """Test successful retrieval of game instructions"""

    # Test case 1: Get prisoners dilemma instructions
    response = client.post(
        "/user/get-game-instructions", json={"game_name": "prisoners_dilemma"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "starter_code" in data
    assert "game_instructions" in data
    assert "Prisoner's Dilemma Game Instructions" in data["game_instructions"]

    # Test case 2: Get greedy pig instructions
    response = client.post(
        "/user/get-game-instructions", json={"game_name": "greedy_pig"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "starter_code" in data
    assert "game_instructions" in data
    assert "Greedy Pig Game Instructions" in data["game_instructions"]


def test_get_game_instructions_exceptions(client):
    """Test error cases for getting game instructions"""

    # Test case 1: Non-existent game
    response = client.post(
        "/user/get-game-instructions", json={"game_name": "non_existent_game"}
    )
    assert response.status_code == 400
    assert "Unknown game" in response.json()["detail"]

    # Test case 2: Empty game name
    response = client.post("/user/get-game-instructions", json={"game_name": ""})
    assert response.status_code == 422

    # Test case 3: Invalid JSON
    response = client.post("/user/get-game-instructions", content="invalid json")
    assert response.status_code == 422


def test_get_available_games(client):
    """Test retrieval of available games list"""

    response = client.post("/user/get-available-games")
    assert response.status_code == 200
    games = response.json()["games"]
    assert "prisoners_dilemma" in games
    assert "greedy_pig" in games


def test_get_published_results_for_league_success(
    client,
    setup_test_league: League,
    setup_teams: list[Team],
    setup_simulation_results: None,
):
    """Test successful retrieval of published league results"""

    # Test case 1: Get results with markdown feedback
    response = client.post(
        "/user/get-published-results-for-league", json={"name": "game_test_league"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert data["league_name"] == "game_test_league"
    assert "# Test Results" in data["feedback"]
    assert data["active"] is True

    # Verify expected data structure
    assert "total_points" in data
    assert "num_simulations" in data
    assert "table" in data
    assert "rewards" in data


def test_get_published_results_for_league_exceptions(client):
    """Test error cases for getting published league results"""

    # Test case 1: Non-existent league
    response = client.post(
        "/user/get-published-results-for-league", json={"name": "non_existent_league"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # Test case 2: Empty league name
    response = client.post("/user/get-published-results-for-league", json={"name": ""})
    assert response.status_code == 422

    # Test case 3: League with no published results returns null
    response = client.post(
        "/user/get-published-results-for-league",
        json={"name": "unassigned"},  # Using existing unassigned league
    )
    assert response.status_code == 200
    assert response.json() is None


def test_get_published_results_for_all_leagues_success(
    client,
    setup_test_league: League,
    setup_teams: list[Team],
    setup_simulation_results: None,
):
    """Test successful retrieval of all published league results"""

    response = client.get("/user/get-published-results-for-all-leagues")
    assert response.status_code == 200
    data = response.json()
    assert "all_results" in data

    # Verify result structure
    results = data["all_results"]
    assert len(results) > 0
    for result in results:
        assert "league_name" in result
        assert "total_points" in result
        assert "table" in result
        assert "num_simulations" in result
        assert "rewards" in result
        assert "feedback" in result
        assert "active" in result


def test_get_published_results_for_all_leagues_empty(client, db_session: Session):
    """Test getting all published results when none exist"""

    # Unpublish all results
    results = db_session.exec(select(SimulationResult)).all()
    for result in results:
        result.published = False
    db_session.commit()

    response = client.get("/user/get-published-results-for-all-leagues")
    assert response.status_code == 200
    assert response.json()["all_results"] == []
