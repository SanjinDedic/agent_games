import os
import sys
import pytest
import time
import shutil
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session, select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from models import League, Team, Submission
from tests.database_setup import setup_test_db

os.environ["TESTING"] = "1"

TEAM_TOKEN = ""
ADMIN_TOKEN = ""

@pytest.fixture(scope="session")
def db_engine():
    engine = setup_test_db(verbose=True)
    yield engine
    try:
        if os.path.exists("../test.db"):
            os.remove("../test.db")
        else:
            os.remove("test.db")
    except FileNotFoundError:
        pass
    finally:
        time.sleep(1)

@pytest.fixture(scope="function")
def db_session(db_engine: Engine):
    with Session(db_engine) as session:
        yield session
        session.rollback()

@pytest.fixture(scope="function")
def client(db_session: Session):
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

    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "number_of_runs": 10},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert simulation_response.status_code == 200
    assert "success" in simulation_response.json()["message"]
