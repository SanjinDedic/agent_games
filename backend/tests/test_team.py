import os
from unittest.mock import patch

import database
import pytest
from api import app
from config import ROOT_DIR
from database import get_db_engine
from fastapi.testclient import TestClient
from models_db import Submission, Team
from sqlmodel import Session, select
from tests.database_setup import setup_test_db

os.environ["TESTING"] = "1"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    setup_test_db()


@pytest.fixture(scope="module")
def db_session():
    engine = get_db_engine()
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture(scope="module")
def client(db_session):
    def get_db_session_override():
        return db_session

    app.dependency_overrides[get_db_engine] = get_db_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def admin_token(client):
    login_response = client.post(
        "/admin_login", json={"username": "Administrator", "password": "BOSSMAN"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["data"]["access_token"]
    return token


# ----------- Team Login ------------


@pytest.fixture(scope="module")
def team_token(client):
    response = client.post(
        "/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"}
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return token


def test_team_login(client):
    response = client.post(
        "/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]
    print("valid credentials", response.json())

    response = client.post(
        "/team_login", json={"name": "BrunswickSC1", "password": "wrongpass"}
    )
    assert response.json() == {
        "status": "failed",
        "message": "Invalid team password",
        "data": None,
    }
    print("invalid creds", response.json())

    response = client.post(
        "/team_login", json={"team": "BrunswickSC1", "password": "wrongpass"}
    )
    assert response.status_code == 422

    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": ""})
    assert response.status_code == 422

    response = client.post("/team_login", json={"name": " ", "password": "ighEMkOP"})
    assert response.status_code == 422

    response = client.post("/team_login", json={"name": "", "password": "password"})
    assert response.status_code == 422
    assert "must not be empty" in response.json()["detail"][0]["msg"]

    response = client.post("/team_login", json={"name": "   ", "password": "password"})
    assert response.status_code == 422
    assert "must not be empty" in response.json()["detail"][0]["msg"]

    response = client.post("/team_login", json={"name": "username", "password": ""})
    assert response.status_code == 422
    assert "must not be empty" in response.json()["detail"][0]["msg"]

    response = client.post("/team_login", json={"name": "username", "password": "  "})
    assert response.status_code == 422
    assert "must not be empty" in response.json()["detail"][0]["msg"]


# ----------- Team Creation -----------


def test_team_create(client, db_session, admin_token):
    team_name = "new_test_team"
    team_password = "new_test_password"
    team_school = "new_test_school"
    response = client.post(
        "/team_create",
        json={"name": team_name, "password": team_password, "school_name": team_school},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert "name" in response.json()["data"]
    assert "id" in response.json()["data"]
    assert "league_id" in response.json()["data"]
    assert "league" in response.json()["data"]

    team = db_session.exec(select(Team).where(Team.name == team_name)).one_or_none()
    assert team is not None
    assert team.name == team_name
    assert team.school_name == team_school
    assert team.verify_password(team_password)

    response = client.post(
        "/team_create",
        json={"name": team_name, "password": team_password, "school_name": team_school},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "Server error: Team already exists"

    response = client.post(
        "/team_create",
        json={"name": "missing_fields_team"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422

    response = client.post(
        "/team_create",
        json={"name": "missing_fields_team", "school": team_school},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422

    response = client.post(
        "/team_create",
        json={"password": team_password, "school": team_school},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422

    response = client.post(
        "/team_create",
        json={"name": team_name, "password": team_password, "school_name": team_school},
    )
    assert response.status_code == 401

    # test logging in as the created team
    response = client.post(
        "/team_login", json={"name": team_name, "password": team_password}
    )
    print(response.json())
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]


def test_delete_team(client, admin_token):
    team_name = "test_team"
    team_password = "test_password"
    team_school = "test_school"
    response = client.post(
        "/team_create",
        json={"name": team_name, "password": team_password, "school_name": team_school},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    response = client.post(
        "/delete_team",
        json={"name": team_name},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert (
        response.json()["message"]
        == f"Team '{team_name}' and its associated files deleted successfully"
    )

    response = client.post(
        "/delete_team",
        json={"name": "non_existent_team"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "Team 'non_existent_team' not found" in response.json()["message"]


# ----------- Agent Submission # -----------


@patch("validation.run_validation_simulation")
def test_submit_agent(mock_validation, client, db_session, team_token):
    # Mock successful validation result
    mock_validation.return_value = ("Test feedback", {"points": {"BrunswickSC1": 100}})

    code = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 15:
            return 'bank'
        return 'continue'
"""
    submission_response = client.post(
        "/submit_agent",
        json={"code": code, "team_name": "BrunswickSC1", "league_name": "comp_test"},
        headers={"Authorization": f"Bearer {team_token}"},
    )
    assert submission_response.status_code == 200
    assert "Code submitted successfully." in submission_response.json()["message"]


# -----------Get All Teams # -----------


def test_get_all_teams(client, db_session):
    # Get all teams from the database
    response = client.get("/get_all_teams")
    assert response.status_code == 200
    print("Response JSON:")
    print(response.json())
    # Check if the response contains all the teams
    teams = db_session.exec(select(Team)).all()
    assert len(response.json()["data"]["all_teams"]) == len(teams)

    # Check if the team names match
    team_names = [team.name for team in teams]
    response_names = [team["name"] for team in response.json()["data"]["all_teams"]]
    print("Team names:")
    print(team_names)
    print("Response names:")
    print(response_names)
    assert sorted(team_names) == sorted(response_names)


# -----------League Assign # -----------


def test_league_assign(client, team_token):
    league_name = "unassigned"
    team_name = "BrunswickSC1"
    response = client.post(
        "/league_assign",
        json={"name": league_name},
        headers={"Authorization": f"Bearer {team_token}"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": f"Team '{team_name}' assigned to league '{league_name}'",
        "data": None,
    }


def test_submit_agent_errors(client, db_session, team_token):
    # Test submitting unsafe code
    unsafe_code = """
import os

class CustomPlayer(Player):
    def make_decision(self, game_state):
        os.system('rm -rf /')
        return 'continue'
    """
    response = client.post(
        "/submit_agent",
        json={"code": unsafe_code},
        headers={"Authorization": f"Bearer {team_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "Agent code is not safe" in response.json()["message"]

    # Test submitting when team is assigned to the 'unassigned' league
    team = database.get_team(db_session, "BrunswickSC1")
    unassigned_league = database.get_league(db_session, "unassigned")
    team.league_id = unassigned_league.id
    db_session.commit()

    safe_code = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 'continue'
    """
    response = client.post(
        "/submit_agent",
        json={"code": safe_code},
        headers={"Authorization": f"Bearer {team_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "Team is not assigned to a valid league" in response.json()["message"]

    # Reassign the team to a league for other tests
    league = database.get_league(db_session, "comp_test")
    team.league_id = league.id
    db_session.commit()


def test_submit_agent_with_unsafe_code(client, db_session, team_token):
    unsafe_code = """
import os

class CustomPlayer(Player):
    def make_decision(self, game_state):
        os.system('rm -rf /')
        return 'continue'
    """
    response = client.post(
        "/submit_agent",
        json={"code": unsafe_code},
        headers={"Authorization": f"Bearer {team_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "Agent code is not safe" in response.json()["message"]


def test_submit_agent_exceed_submission_limit(client, db_session, team_token):
    safe_code = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 'continue'
    """

    # Submit 2 times (allowed)
    for _ in range(5):
        response = client.post(
            "/submit_agent",
            json={"code": safe_code},
            headers={"Authorization": f"Bearer {team_token}"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    # 5th submission within a minute (should be rejected)
    response = client.post(
        "/submit_agent",
        json={"code": safe_code},
        headers={"Authorization": f"Bearer {team_token}"},
    )

    print("Response JSON:", response.json())
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "You can only make 5 submissions per minute" in response.json()["message"]


def test_league_assign_error(client, team_token, mocker):
    # Mock database.assign_team_to_league to raise an exception
    mocker.patch(
        "database.assign_team_to_league",
        side_effect=Exception("Database connection error"),
    )

    response = client.post(
        "/league_assign",
        json={"name": "test_league"},
        headers={"Authorization": f"Bearer {team_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "error",
        "message": "An error occurred while assigning team to leagueDatabase connection error",
        "data": None,  # Added this line
    }


def test_get_all_teams_error(client, db_session, mocker):
    # Mock database.get_all_teams to raise an exception
    mocker.patch("database.get_all_teams", side_effect=Exception("Database error"))

    response = client.get("/get_all_teams")

    assert response.status_code == 200
    assert response.json() == {
        "status": "error",
        "message": "An error occurred while retrieving teams",
        "data": None,  # Added this line
    }
