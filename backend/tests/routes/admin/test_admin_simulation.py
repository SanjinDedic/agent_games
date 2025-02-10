import json
from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import League, SimulationResult, Submission, Team
from backend.routes.auth.auth_core import create_access_token


def create_test_league_with_teams(db_session: Session) -> League:
    """Helper function to create a test league with teams and submissions"""
    # Create a test league
    league = League(
        name="sim_test_league",
        game="prisoners_dilemma",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
    )
    db_session.add(league)
    db_session.commit()

    # Create test teams with submissions
    teams = []
    for i in range(3):
        team = Team(
            name=f"sim_team_{i}",
            school_name=f"School {i}",
            password_hash="hash",
            league_id=league.id,
        )
        db_session.add(team)
        db_session.commit()
        teams.append(team)

        # Add a simple valid submission for each team
        submission = Submission(
            code=f"""
from games.prisoners_dilemma.player import Player
class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
""",
            timestamp=datetime.now(),
            team_id=team.id,
        )
        db_session.add(submission)

    db_session.commit()
    return league


def test_run_simulation_success(client, auth_headers, db_session):
    """Test successful simulation execution scenarios"""

    # Create test league with teams and submissions
    league = create_test_league_with_teams(db_session)

    # Test case 1: Basic simulation with default parameters
    response = client.post(
        "/admin/run-simulation",
        headers=auth_headers,
        json={"league_id": league.id, "num_simulations": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    result_data = data["data"]
    assert "total_points" in result_data
    assert "table" in result_data
    assert "id" in result_data  # Simulation ID should be present

    # Verify simulation was saved in database
    sim_result = db_session.exec(
        select(SimulationResult).where(SimulationResult.id == result_data["id"])
    ).first()
    assert sim_result is not None
    assert sim_result.num_simulations == 10

    # Test case 2: Simulation with custom rewards
    response = client.post(
        "/admin/run-simulation",
        headers=auth_headers,
        json={
            "league_id": league.id,
            "num_simulations": 5,
            "custom_rewards": [10, 8, 6, 4, 2],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    result_data = data["data"]
    assert result_data["rewards"] == [10, 8, 6, 4, 2]

    # Test case 3: Simulation for greedy pig league
    gp_league = League(
        name="gp_sim_league",
        game="greedy_pig",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
    )
    db_session.add(gp_league)
    db_session.commit()

    # Add a team with valid greedy pig submission
    team = Team(
        name="gp_team",
        school_name="GP School",
        password_hash="hash",
        league_id=gp_league.id,
    )
    db_session.add(team)
    db_session.commit()

    submission = Submission(
        code="""
from games.greedy_pig.player import Player
class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "bank" if game_state["unbanked_money"][self.name] > 20 else "continue"
""",
        timestamp=datetime.now(),
        team_id=team.id,
    )
    db_session.add(submission)
    db_session.commit()

    response = client.post(
        "/admin/run-simulation",
        headers=auth_headers,
        json={"league_id": gp_league.id, "num_simulations": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_run_simulation_exceptions(client, auth_headers, db_session):
    """Test error cases for running simulations"""

    # Test case 1: Non-existent league
    response = client.post(
        "/admin/run-simulation",
        headers=auth_headers,
        json={"league_id": 99999, "num_simulations": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()

    # Test case 2: Invalid number of simulations
    league = create_test_league_with_teams(db_session)
    response = client.post(
        "/admin/run-simulation",
        headers=auth_headers,
        json={"league_id": league.id, "num_simulations": -1},
    )
    assert response.status_code == 422

    # Test case 3: League with no teams
    empty_league = League(
        name="empty_sim_league",
        game="prisoners_dilemma",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
    )
    db_session.add(empty_league)
    db_session.commit()

    response = client.post(
        "/admin/run-simulation",
        headers=auth_headers,
        json={"league_id": empty_league.id, "num_simulations": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    # Verify only validation players are present
    validation_players = [
        "AlwaysCooperate",
        "AlwaysDefect",
        "TitForTat",
        "GradualPlayer",
        "RandomPlayer",
    ]
    print("Here are the playas", data["data"]["total_points"].keys())
    assert all(
        player in validation_players for player in data["data"]["total_points"].keys()
    )

    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/admin/run-simulation", json={"league_id": league.id, "num_simulations": 10}
    )
    assert response.status_code == 401

    # Test case 5: Invalid custom rewards format
    response = client.post(
        "/admin/run-simulation",
        headers=auth_headers,
        json={
            "league_id": league.id,
            "num_simulations": 10,
            "custom_rewards": "invalid",  # Should be a list
        },
    )
    assert response.status_code == 422


def test_publish_results_success(client, auth_headers, db_session):
    """Test successful publishing of simulation results"""

    # Create test league
    league = League(
        name="sim_test_league",
        game="prisoners_dilemma",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
    )
    db_session.add(league)
    db_session.commit()

    # Create some test teams
    teams = []
    for i in range(3):
        team = Team(
            name=f"sim_team_{i}",
            school_name=f"School {i}",
            password_hash="hash",
            league_id=league.id,
        )
        db_session.add(team)
        db_session.commit()
        teams.append(team)

    # Create two test simulation results
    sim_result1 = SimulationResult(
        league_id=league.id,
        timestamp=datetime.now(),
        num_simulations=10,
        custom_rewards="[10, 8, 6, 4, 2]",
        published=False,
    )
    sim_result2 = SimulationResult(
        league_id=league.id,
        timestamp=datetime.now(),
        num_simulations=10,
        custom_rewards="[10, 8, 6, 4, 2]",
        published=False,
    )
    db_session.add(sim_result1)
    db_session.add(sim_result2)
    db_session.commit()
    db_session.refresh(sim_result1)
    db_session.refresh(sim_result2)

    # Test case 1: Basic result publishing with string feedback
    response = client.post(
        "/admin/publish-results",
        headers=auth_headers,
        json={
            "league_name": league.name,
            "id": sim_result1.id,
            "feedback": "Test feedback",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "published successfully" in data["message"]

    # Refresh database state
    db_session.refresh(sim_result1)
    db_session.refresh(sim_result2)

    # Verify first result was published and has string feedback
    assert sim_result1.published is True
    assert sim_result1.feedback_str == "Test feedback"
    assert sim_result1.feedback_json is None

    # Test case 2: Publishing with JSON feedback
    json_feedback = {
        "analysis": {"performance": "good", "recommendations": ["improve strategy"]}
    }

    response = client.post(
        "/admin/publish-results",
        headers=auth_headers,
        json={
            "league_name": league.name,
            "id": sim_result2.id,
            "feedback": json_feedback,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Refresh database state
    db_session.refresh(sim_result1)
    db_session.refresh(sim_result2)

    # Verify second result was published and first was unpublished
    assert sim_result2.published is True
    assert sim_result2.feedback_json == json.dumps(json_feedback)
    assert sim_result2.feedback_str is None
    assert sim_result1.published is False  # Previous result should be unpublished


def test_publish_results_exceptions(client, auth_headers, db_session):
    """Test error cases for publishing simulation results"""

    # Create test league
    league = create_test_league_with_teams(db_session)

    # Create a test simulation result
    sim_result = SimulationResult(
        league_id=league.id, timestamp=datetime.now(), num_simulations=10
    )
    db_session.add(sim_result)
    db_session.commit()

    # Test case 1: Non-existent league
    response = client.post(
        "/admin/publish-results",
        headers=auth_headers,
        json={"league_name": "non_existent_league", "id": sim_result.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()

    # Test case 2: Non-existent simulation result
    response = client.post(
        "/admin/publish-results",
        headers=auth_headers,
        json={"league_name": league.name, "id": 99999},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()

    # Test case 3: Unauthorized access (no token)
    response = client.post(
        "/admin/publish-results", json={"league_name": league.name, "id": sim_result.id}
    )
    assert response.status_code == 401

    # Test case 4: Non-admin token
    non_admin_token = create_access_token(
        data={"sub": "user", "role": "student"}, expires_delta=timedelta(minutes=30)
    )
    response = client.post(
        "/admin/publish-results",
        headers={"Authorization": f"Bearer {non_admin_token}"},
        json={"league_name": league.name, "id": sim_result.id},
    )
    assert response.status_code == 403


def test_get_simulator_logs_success(client, auth_headers):
    """Test successful retrieval of simulator logs"""

    response = client.get("/admin/get-simulator-logs", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "logs" in data["data"]


def test_get_simulator_logs_exceptions(client):
    """Test error cases for retrieving simulator logs"""

    # Test case 1: Unauthorized access (no token)
    response = client.get("/admin/get-simulator-logs")
    assert response.status_code == 401

    # Test case 2: Non-admin token
    non_admin_token = create_access_token(
        data={"sub": "user", "role": "student"}, expires_delta=timedelta(minutes=30)
    )
    response = client.get(
        "/admin/get-simulator-logs",
        headers={"Authorization": f"Bearer {non_admin_token}"},
    )
    assert response.status_code == 403
