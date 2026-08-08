import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from backend.tests.conftest import add_submission
from backend.database.db_models import UNASSIGNED_LEAGUE_NAME, League, SimulationResult, Team
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


def create_test_league_with_teams(db_session: Session) -> League:
    """Create a test league with teams and submissions."""
    # Create a test league
    league = League(
        name="inst_sim_test_league",
        game="prisoners_dilemma",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
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
        )
        db_session.add(team)
        db_session.commit()
        teams.append(team)

        # Add a simple valid submission for each team
        add_submission(
            db_session,
            code=f"""
from games.prisoners_dilemma.player import Player
class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
""",
            timestamp=utc_now(),
            team_id=team.id,
        )

    db_session.commit()
    return league


@pytest.fixture
def simulation_setup(db_session: Session) -> tuple:
    """A league and team, for simulation tests."""
    db_session.commit()
    
    league = create_test_league_with_teams(db_session)
    
    # Get the first team
    team = db_session.exec(
        select(Team).where(Team.league_id == league.id)
    ).first()
    
    # Create token
    token = create_access_token(
        data={
            "sub": "test_owner",
            "role": "owner",
        },
        expires_delta=timedelta(minutes=30),
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    return league, team, token, headers


def test_run_simulation_success(client, simulation_setup, db_session):
    """Test successful simulation execution"""
    league, team, _, headers = simulation_setup
    
    # Patch the Celery task so no worker round-trip happens
    with patch("backend.routes.owner.owner_router.run_simulation") as mock_task:
        # The router awaits poll_task_result, which reads ready()/successful()/.result
        mock_async = mock_task.delay.return_value
        mock_async.ready.return_value = True
        mock_async.successful.return_value = True
        mock_async.result = {
            "status": "success",
            "simulation_results": {
                "total_points": {team.name: 100},
                "num_simulations": 10,
                "table": {"wins": {team.name: 5}, "defections": {team.name: 2}, "collusions": {team.name: 8}},
            },
            "feedback": "Test feedback",
            "player_feedback": {"test_player": "feedback"},
        }


        # Test basic simulation
        response = client.post(
            "/owner/run-simulation",
            headers=headers,
            json={"league_id": league.id, "num_simulations": 10},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify simulation details in response
        result_data = data
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
            "/owner/run-simulation",
            headers=headers,
            json={
                "league_id": league.id,
                "num_simulations": 5,
                "custom_rewards": custom_rewards,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rewards"] == custom_rewards


def test_run_simulation_worker_error_surfaces_and_stores_nothing(
    client, simulation_setup, db_session
):
    """A run the worker reports as failed (e.g. no loadable players) must
    return 400 with the worker's message and must NOT store a result row —
    storing one renders as an empty rankings table with no explanation."""
    league, team, _, headers = simulation_setup

    before = len(db_session.exec(select(SimulationResult)).all())

    with patch(
        "backend.routes.owner.owner_router.run_simulation"
    ) as mock_task:
        mock_async = mock_task.delay.return_value
        mock_async.ready.return_value = True
        mock_async.successful.return_value = True
        mock_async.result = {
            "status": "error",
            "message": "No players loaded for simulation",
            "simulation_results": {
                "total_points": {},
                "num_simulations": 10,
                "table": {},
            },
        }

        response = client.post(
            "/owner/run-simulation",
            headers=headers,
            json={"league_id": league.id, "num_simulations": 10},
        )

    assert response.status_code == 400
    assert "no players loaded" in response.json()["detail"].lower()
    after = len(db_session.exec(select(SimulationResult)).all())
    assert after == before


def test_run_simulation_rejects_unassigned_league(
    client, simulation_setup, db_session
):
    """The auto-created 'unassigned' placeholder league cannot be simulated"""
    _, _, _, headers = simulation_setup

    unassigned = db_session.exec(
        select(League).where(League.name == UNASSIGNED_LEAGUE_NAME)
    ).one()

    response = client.post(
        "/owner/run-simulation",
        headers=headers,
        json={"league_id": unassigned.id, "num_simulations": 10},
    )
    assert response.status_code == 400
    assert "unassigned" in response.json()["detail"].lower()


def test_run_simulation_failures(client, simulation_setup, db_session):
    """Test failure cases for running simulations"""
    league, team, _, headers = simulation_setup
    
    # Test case 1: Non-existent league
    response = client.post(
        "/owner/run-simulation",
        headers=headers,
        json={"league_id": 99999, "num_simulations": 10},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    
    # Test case 2: Invalid number of simulations
    response = client.post(
        "/owner/run-simulation",
        headers=headers,
        json={"league_id": league.id, "num_simulations": -1},
    )
    assert response.status_code == 422
    
    # Test case 3: Unauthorized access (no token)
    response = client.post(
        "/owner/run-simulation",
        json={"league_id": league.id, "num_simulations": 10},
    )
    assert response.status_code == 401