import os
import sys
import pytest
import time
from fastapi.testclient import TestClient
from sqlmodel import Session, select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from models_db import Team
from tests.database_setup import setup_test_db
os.environ["TESTING"] = "1"

ADMIN_VALID_TOKEN = ""
TEAM_TOKEN = ""

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    setup_test_db()

@pytest.fixture(scope="function")
def db_session():
    engine = get_db_engine()
    with Session(engine) as session:
        yield session
        session.rollback()

@pytest.fixture(scope="function")
def client(db_session):
    def get_db_session_override():
        return db_session

    app.dependency_overrides[get_db_engine] = get_db_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_get_token(client: TestClient):
    global ADMIN_VALID_TOKEN

    login_response = client.post("/admin_login", json={"username": "Administrator", "password": "BOSSMAN"})
    assert login_response.status_code == 200
    token = login_response.json()["data"]["access_token"]
    ADMIN_VALID_TOKEN = token

def test_team_login(client: TestClient):
    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"})
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]

    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "wrongpass"})
    assert response.json() == {'status': 'failed', 'message': 'Invalid team password', 'data': None}

    response = client.post("/team_login", json={"team": "BrunswickSC1", "password": "wrongpass"})
    assert response.status_code == 422

    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": ""})
    assert response.status_code == 422

    response = client.post("/team_login", json={"name": " ", "password": "ighEMkOP"})
    assert response.status_code == 422

## Review the test (sending admin token instead of team token on team_login)
def test_league_assign(client: TestClient, db_session):
    global TEAM_TOKEN, ADMIN_VALID_TOKEN
    # Get the token for the team
    team_name = "BrunswickSC1"
    team_login_response = client.post(
        "/team_login", json={"name": f"{team_name}", "password": "ighEMkOP"}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert team_login_response.status_code == 200
    TEAM_TOKEN = team_login_response.json()["data"]["access_token"]
    print("Team Token:", TEAM_TOKEN)
    league_name = "unassigned"
    # Assign the team to the league
    response = client.post(
        "/league_assign",
        json={"name":f"{league_name}"},
        headers={"Authorization": f"Bearer {TEAM_TOKEN}"})
    print("League Assign Response:", response.json())
    assert response.status_code == 200
    assert response.json() == {"status":"success", "message": f"Team '{team_name}' assigned to league '{league_name}'", "data": None}




def test_team_create(client: TestClient, db_session):
    global ADMIN_VALID_TOKEN
    # Create a team
    team_name = "new_test_team"
    team_password = "new_test_password"
    team_school = "new_test_school"
    response = client.post("/team_create", json={"name": team_name, "password": team_password, "school_name": team_school}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]
    assert response.json()["data"]["token_type"] == "bearer"

    # Check if the team is created in the database
    team = db_session.exec(select(Team).where(Team.name == team_name)).one_or_none()
    assert team is not None
    assert team.name == team_name
    assert team.school_name == team_school
    assert team.verify_password(team_password)

    # Try to create a team with the same name
    response = client.post("/team_create", json={"name": team_name, "password": team_password, "school_name": team_school}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json()["status"] == "failed"

    # Try to create a team with missing fields
    response = client.post("/team_create", json={"name": "missing_fields_team"}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 422

    response = client.post("/team_create", json={"name": "missing_fields_team", "school": team_school}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 422

    response = client.post("/team_create", json={"password": team_password, "school": team_school}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 422

    # Try to create a team with no authorization
    response = client.post("/team_create", json={"name": team_name, "password": team_password, "school_name": team_school})
    assert response.status_code == 401

def test_delete_team(client: TestClient):
    global ADMIN_VALID_TOKEN
    # Create a team
    team_name = "test_team"
    team_password = "test_password"
    team_school = "test_school"
    response = client.post("/team_create", json={"name": team_name, "password": team_password, "school_name": team_school}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200

    # Delete the team
    response = client.post("/delete_team", json={"name": team_name}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    print("Delete Team Response:", response.json())
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["message"] == f"Team '{team_name}' deleted successfully"

    # Try to delete a non-existent team
    response = client.post("/delete_team", json={"name": "non_existent_team"}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "Team 'non_existent_team' not found"