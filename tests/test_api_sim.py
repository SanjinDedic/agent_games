import os
import sys
import pytest
import time
from fastapi.testclient import TestClient
from sqlmodel import Session

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from models import League
from tests.database_setup import setup_test_db
os.environ["TESTING"] = "1"

ADMIN_VALID_TOKEN = ""

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
    global TEAM_TOKEN

    # Get the token for the team
    team_login_response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"})
    assert team_login_response.status_code == 200
    TEAM_TOKEN = team_login_response.json()["access_token"]
    assert TEAM_TOKEN != ""


def test_admin_login(client: TestClient):
    global ADMIN_TOKEN
    # Get the token for the admin
    admin_login_response = client.post("/admin_login", json={"username": "Administrator", "password": "BOSSMAN"})
    assert admin_login_response.status_code == 200
    ADMIN_TOKEN = admin_login_response.json()["access_token"]
    assert ADMIN_TOKEN != ""

def test_run_simulation(client: TestClient):
    global TEAM_TOKEN
    global ADMIN_TOKEN
    print("ADMIN_TOKEN", ADMIN_TOKEN, "simulation called")
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert simulation_response.status_code == 200
    assert "results" in simulation_response.json()