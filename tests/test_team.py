import os
import sys
import pytest
import time
from fastapi.testclient import TestClient
from sqlmodel import Session, select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from models import Team
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

def test_team_login(client: TestClient):
    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"})
    assert response.status_code == 200
    assert "access_token" in response.json()

    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "wrongpass"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid team credentials"}

    response = client.post("/team_login", json={"team": "BrunswickSC1", "password": "wrongpass"})
    assert response.status_code == 422

    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": ""})
    assert response.status_code == 422

    response = client.post("/team_login", json={"name": " ", "password": "ighEMkOP"})
    assert response.status_code == 422


def test_league_assign(client: TestClient, db_session):
    global TEAM_TOKEN
    # Get the token for the team
    team_name = "BrunswickSC1"
    team_login_response = client.post(
        "/team_login", json={"name": f"{team_name}", "password": "ighEMkOP"})
    assert team_login_response.status_code == 200
    TEAM_TOKEN = team_login_response.json()["access_token"]
    print("Team Token:", TEAM_TOKEN)
    league_name = "unassigned"
    # Assign the team to the league
    response = client.post(
        "/league_assign",
        json={"name":f"{league_name}"},
        headers={"Authorization": f"Bearer {TEAM_TOKEN}"})
    print("League Assign Response:", response.json())
    assert response.status_code == 200
    assert response.json() == {"message": f"Team '{team_name}' assigned to league '{league_name}'"}




def test_team_create(client: TestClient, db_session):
    # Create a team
    team_name = "new_test_team"
    team_password = "new_test_password"
    team_school = "new_test_school"
    response = client.post("/team_create", json={"name": team_name, "password": team_password, "school_name": team_school})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

    # Check if the team is created in the database
    team = db_session.exec(select(Team).where(Team.name == team_name)).one_or_none()
    assert team is not None
    assert team.name == team_name
    assert team.school_name == team_school
    assert team.verify_password(team_password)

    # Try to create a team with the same name
    response = client.post("/team_create", json={"name": team_name, "password": team_password, "school_name": team_school})
    assert response.status_code == 200
    assert response.json()["status"] == "failed"

    # Try to create a team with missing fields
    response = client.post("/team_create", json={"name": "missing_fields_team", "password": team_password})
    assert response.status_code == 422

    response = client.post("/team_create", json={"name": "missing_fields_team", "school": team_school})
    assert response.status_code == 422

    response = client.post("/team_create", json={"password": team_password, "school": team_school})
    assert response.status_code == 422



def test_delete_team(client: TestClient):
    # Create a team
    team_name = "test_team"
    team_password = "test_password"
    team_school = "test_school"
    response = client.post("/team_create", json={"name": team_name, "password": team_password, "school_name": team_school})
    assert response.status_code == 200

    # Delete the team
    response = client.post("/delete_team", json={"name": team_name})
    print("Delete Team Response:", response.json())
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["message"] == f"Team '{team_name}' deleted successfully"

    # Try to delete a non-existent team
    response = client.post("/delete_team", json={"name": "non_existent_team"})
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "Team 'non_existent_team' not found"