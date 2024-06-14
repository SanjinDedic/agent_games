import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from models_db import Team
from tests.database_setup import setup_test_db

os.environ["TESTING"] = "1"

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

def test_get_all_teams(client: TestClient, db_session: Session):
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