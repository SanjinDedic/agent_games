import os
import sys
import pytest
import time
import shutil
from fastapi.testclient import TestClient
from sqlmodel import Session

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from models import League
from tests.database_setup import setup_test_db
os.environ["TESTING"] = "1"

ADMIN_VALID_TOKEN = ""

@pytest.fixture(scope="session")
def db_engine():
    engine = setup_test_db(verbose=True)
    yield engine
    if os.path.exists("../test.db"):
        os.remove("../test.db")
    if os.path.exists("/test.db"):
        os.remove("/test.db")
        time.sleep(1)

@pytest.fixture(scope="function")
def db_session(db_engine):
    with Session(db_engine) as session:
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
    token = login_response.json()["access_token"]
    ADMIN_VALID_TOKEN = token


def test_league_creation(client: TestClient):

    response = client.post("/league_create", json={"name": "week1", "game": "greedy_pig"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]

    response = client.post("/league_create")
    assert response.status_code == 422
    
    response = client.post("/league_create", json={"name": "", "game": "greedy_pig"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Name is Empty"}

    response = client.post("/league_create", json={"name": "week2", "game": "greedy_pig"}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]
    #cleanup
    shutil.rmtree(f"games/greedy_pig/leagues/user/week1")
    assert not os.path.isdir(f"games/greedy_pig/leagues/user/week1")
    shutil.rmtree(f"games/greedy_pig/leagues/admin/week2")
    assert not os.path.isdir(f"games/greedy_pig/leagues/admin/week2")


def test_league_join(client: TestClient):

    response = client.post("/league_join/MQ%3D%3D", json={"name": "std", "password": "pass", "school": "abc"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_league_folder_creation(client: TestClient):
    league_name = "test_league_admin"
    response = client.post("/league_create", json={"name": league_name, "game": "greedy_pig"}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]
    assert os.path.isdir(f"games/greedy_pig/leagues/admin/{league_name}")
    shutil.rmtree(f"games/greedy_pig/leagues/admin/{league_name}")
    assert not os.path.isdir(f"games/greedy_pig/leagues/user/{league_name}")


def test_league_folder_creation_no_auth(client: TestClient):
    league_name = "test_league_user"
    response = client.post("/league_create", json={"name": league_name, "game": "greedy_pig"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]
    assert os.path.isdir(f"games/greedy_pig/leagues/user/{league_name}")
    # cleanup
    shutil.rmtree(f"games/greedy_pig/leagues/user/{league_name}")
    assert not os.path.isdir(f"games/greedy_pig/leagues/user/{league_name}")
    