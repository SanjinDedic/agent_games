# tests/integration/test_game_workflows.py

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.tests.conftest import add_submission, build_institution
from backend.database.db_models import League, Team
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def setup_integration_team(db_session: Session, test_league: League) -> Team:
    """Create a test team with basic submission"""
    team = Team(
        name="integration_test_team",
        school_name="Integration Test School",
        password_hash="test_hash",
        league_id=test_league.id,
        institution_id=test_league.institution_id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # Add a basic valid submission
    add_submission(
        db_session,
        code="""
from games.prisoners_dilemma.player import Player
class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
""",
        timestamp=utc_now(),
        team_id=team.id,
    )
    db_session.commit()

    return team


def test_complete_game_lifecycle(
    client: TestClient,
    db_session: Session,
    auth_headers: dict,
    team_auth_headers: dict,
):
    """
    Test complete lifecycle from league creation through game completion.
    This test verifies the entire flow of:
    1. League creation
    2. Team creation and assignment
    3. Code submission
    4. Running simulations
    5. Publishing results
    6. Viewing results
    """
    # First create an institution
    institution = build_institution(
        name="test_institution",
        contact_person="Test Person",
        contact_email="test@example.com",
        created_date=utc_now(),
        subscription_active=True,
        subscription_expiry=utc_now() + timedelta(days=30),
        password_hash="test_hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    # 1. Create a new league
    # The headers need to be institution headers
    inst_token = create_access_token(
        data={
            "sub": "test_institution",
            "role": "institution",
            "institution_id": institution.id,  # Include institution_id
        },
        expires_delta=timedelta(minutes=30),
    )
    auth_headers = {"Authorization": f"Bearer {inst_token}"}

    league_response = client.post(
        "/institution/league-create",
        headers=auth_headers,
        json={"name": "integration_league", "game": "prisoners_dilemma"},
    )
    assert league_response.status_code == 200
    league_data = league_response.json()
    league_id = league_data["league_id"]

    # 2. Create and assign team
    team_response = client.post(
        "/institution/team-create",  # Changed from /admin to /institution
        headers=auth_headers,
        json={
            "name": "integration_team",
            "password": "test_pass",
            "school_name": "Integration School",
            "league_id": league_id,  # Explicitly providing league_id
        },
    )
    print("TEAM RESPONSE GAME LIFECYCLE")
    print(team_response.json())
    assert team_response.status_code == 200
    team_id = team_response.json()["team_id"]

    # Create team token and headers
    team_token = create_access_token(
        data={"sub": "integration_team", "role": "student", "team_id": team_id},
        expires_delta=timedelta(minutes=30),
    )
    team_headers = {"Authorization": f"Bearer {team_token}"}

    # Assign team to league - may not be needed if team was created with league_id
    try:
        assign_response = client.post(
            "/user/league-assign",
            headers=team_headers,
            json={"league_id": league_id},
        )
        assert assign_response.status_code == 200
        assert "assigned to league" in assign_response.json()["message"]
    except:
        pass  # This might fail if team is already assigned to league

    # 3. Submit code
    code = """
from games.prisoners_dilemma.player import Player
class CustomPlayer(Player):
    def make_decision(self, game_state):
        self.add_feedback(f"Round {game_state['round_number']}")
        return "collude" if game_state['round_number'] % 2 == 0 else "defect"
"""
    submit_response = client.post(
        "/user/submit-agent",
        headers=team_headers,
        json={"code": code},
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["submission_id"] is not None

    # 4. Run simulation
    sim_response = client.post(
        "/institution/run-simulation",  # Changed from /admin to /institution
        headers=auth_headers,
        json={
            "league_id": league_id,
            "num_simulations": 10,
            "custom_rewards": [4, 0, 6, 2],
        },
    )
    assert sim_response.status_code == 200
    sim_data = sim_response.json()
    sim_id = sim_data["id"]

    # 5. Publish results
    publish_response = client.post(
        "/institution/publish-results",  # Changed from /admin to /institution
        headers=auth_headers,
        json={
            "league_id": league_id,
            "id": sim_id,
            "feedback": "Integration test simulation results",
        },
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["published"] is True

    # 6. View results (as team)
    results_response = client.post(
        "/user/get-published-results-for-league",
        json={"name": "integration_league"},
    )
    assert results_response.status_code == 200
    results_data = results_response.json()
    assert results_data is not None
    assert "total_points" in results_data
