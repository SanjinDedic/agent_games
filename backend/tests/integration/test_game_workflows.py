# tests/integration/test_game_workflows.py

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.tests.conftest import add_submission, build_institution, make_student_token
from backend.database.db_models import League, Team
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def setup_integration_team(db_session: Session, test_league: League) -> Team:
    """Create a test team with a submission for test_league's game (greedy_pig)"""
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
from games.greedy_pig.player import Player
class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 5:
            return "bank"
        return "continue"
""",
        timestamp=utc_now(),
        team_id=team.id,
    )
    db_session.commit()

    return team


@pytest.fixture
def integration_team_headers(setup_integration_team: Team) -> dict:
    """Student headers for the team created by setup_integration_team"""
    return {"Authorization": f"Bearer {make_student_token(setup_integration_team)}"}


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

    # Re-assign the team to the league it was created in - assignment is idempotent
    assign_response = client.post(
        "/user/league-assign",
        headers=team_headers,
        json={"league_id": league_id},
    )
    assert assign_response.status_code == 200
    assert "assigned to league" in assign_response.json()["message"]

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


def test_league_assign_unknown_league(
    client: TestClient, integration_team_headers: dict
):
    """Assigning to a league that doesn't exist is a 404, not a silent no-op."""
    response = client.post(
        "/user/league-assign",
        headers=integration_team_headers,
        json={"league_id": 999999},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_league_assign_keeps_team_in_original_league_on_failure(
    client: TestClient,
    db_session: Session,
    setup_integration_team: Team,
    integration_team_headers: dict,
    test_league: League,
):
    """A failed assignment leaves the team's existing league untouched."""
    response = client.post(
        "/user/league-assign",
        headers=integration_team_headers,
        json={"league_id": 999999},
    )
    assert response.status_code == 404

    db_session.refresh(setup_integration_team)
    assert setup_integration_team.league_id == test_league.id


def test_run_simulation_unknown_league(client: TestClient, auth_headers: dict):
    """Simulating a league that doesn't exist is a 404 (never reaches the worker)."""
    response = client.post(
        "/institution/run-simulation",
        headers=auth_headers,
        json={"league_id": 999999, "num_simulations": 10},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_run_simulation_rejected_on_unassigned_league(
    client: TestClient, db_session: Session, auth_headers: dict
):
    """The 'unassigned' holding league is protected from simulation runs."""
    unassigned = db_session.exec(
        select(League).where(League.name == "unassigned")
    ).one()

    response = client.post(
        "/institution/run-simulation",
        headers=auth_headers,
        json={"league_id": unassigned.id, "num_simulations": 10},
    )
    assert response.status_code == 400
    assert "unassigned" in response.json()["detail"].lower()


def test_run_simulation_rejects_other_institutions_league(
    client: TestClient, db_session: Session, test_league: League
):
    """An institution cannot simulate a league it doesn't own."""
    outsider = build_institution(
        name="outsider_institution",
        contact_email="outsider@example.com",
        created_date=utc_now(),
        password_hash="test_hash",
    )
    db_session.add(outsider)
    db_session.commit()
    db_session.refresh(outsider)

    outsider_token = create_access_token(
        data={
            "sub": "outsider_institution",
            "role": "institution",
            "institution_id": outsider.id,
        },
        expires_delta=timedelta(minutes=30),
    )

    response = client.post(
        "/institution/run-simulation",
        headers={"Authorization": f"Bearer {outsider_token}"},
        json={"league_id": test_league.id, "num_simulations": 10},
    )
    assert response.status_code == 403
