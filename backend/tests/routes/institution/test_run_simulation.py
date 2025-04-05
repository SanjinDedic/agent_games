import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (Institution, League, SimulationResult,
                                        Submission, Team)
from backend.routes.auth.auth_core import create_access_token


def create_test_league_with_teams(db_session: Session, institution_id: int) -> League:
    """Helper function to create a test league with teams and submissions for an institution"""
    # Create a test league
    league = League(
        name="inst_sim_test_league",
        game="prisoners_dilemma",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        institution_id=institution_id,
    )
    db_session.add(league)
    db_session.commit()

    # Create test teams with submissions
    teams = []
    for i in range(3):
        team = Team(
            name=f"inst_sim_team_{i}",
            school_name=f"School {i}",
            password_hash="hash",
            league_id=league.id,
            institution_id=institution_id,
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


@pytest.fixture
def simulation_setup(db_session: Session) -> tuple:
    """Setup institution, league, and team for simulation testing"""
    # Create an institution with docker access
    institution = Institution(
        name="test_institution",
        contact_person="Test Person",
        contact_email="test@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,  # Enable docker access
        password_hash="test_hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)
    
    # Create a league with teams for the institution
    league = create_test_league_with_teams(db_session, institution.id)
    
    # Get the first team
    team = db_session.exec(
        select(Team).where(Team.league_id == league.id)
    ).first()
    
    # Create token
    token = create_access_token(
        data={
            "sub": institution.name,
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(minutes=30),
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    return institution, league, team, token, headers


def test_run_simulation_success(client, simulation_setup, db_session):
    """Test successful simulation execution"""
    institution, league, team, _, headers = simulation_setup
    
    # Need to patch the Docker API call to avoid actual Docker calls
    with patch("httpx.AsyncClient.post") as mock_post:
        # Setup mock response
        mock_response = type('MockResponse', (), {
            'status_code': 200,
            'json': lambda self: {
                "status": "success",
                "simulation_results": {
                    "total_points": {team.name: 100},
                    "num_simulations": 10,
                    "table": {"wins": {team.name: 5}, "defections": {team.name: 2}, "collusions": {team.name: 8}},
                },
                "feedback": "Test feedback",
                "player_feedback": {"test_player": "feedback"},
            }
        })()
        
        # Make the mock post return an awaitable that returns the mock response
        async def mock_post_async(*args, **kwargs):
            return mock_response
        
        mock_post.side_effect = mock_post_async
        
        # Test basic simulation
        response = client.post(
            "/institution/run-simulation",
            headers=headers,
            json={"league_id": league.id, "num_simulations": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify simulation details in response
        assert "data" in data
        result_data = data["data"]
        assert "total_points" in result_data
        assert team.name in result_data["total_points"]
        assert "table" in result_data
        assert "id" in result_data
        
        # Verify simulation was saved in database
        sim_result = db_session.exec(
            select(SimulationResult).where(SimulationResult.id == result_data["id"])
        ).first()
        assert sim_result is not None
        assert sim_result.num_simulations == 10
        
        # Test with custom rewards
        custom_rewards = [10, 8, 6, 4]
        response = client.post(
            "/institution/run-simulation",
            headers=headers,
            json={
                "league_id": league.id,
                "num_simulations": 5,
                "custom_rewards": custom_rewards,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["rewards"] == custom_rewards


def test_run_simulation_failures(client, simulation_setup, db_session):
    """Test failure cases for running simulations"""
    institution, league, team, _, headers = simulation_setup
    
    # Test case 1: Non-existent league
    response = client.post(
        "/institution/run-simulation",
        headers=headers,
        json={"league_id": 99999, "num_simulations": 10},
    )
    assert response.status_code == 200  # API returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    
    # Test case 2: Institution without Docker access
    # Update institution to remove Docker access
    institution.docker_access = False
    db_session.add(institution)
    db_session.commit()
    
    response = client.post(
        "/institution/run-simulation",
        headers=headers,
        json={"league_id": league.id, "num_simulations": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "docker access" in data["message"].lower()
    
    # Test case 3: Invalid number of simulations
    response = client.post(
        "/institution/run-simulation",
        headers=headers,
        json={"league_id": league.id, "num_simulations": -1},
    )
    assert response.status_code == 422
    
    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/institution/run-simulation",
        json={"league_id": league.id, "num_simulations": 10},
    )
    assert response.status_code == 401