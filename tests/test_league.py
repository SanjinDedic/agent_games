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
from models_db import League
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

def test_get_token(client: TestClient):
    global ADMIN_VALID_TOKEN

    login_response = client.post("/admin_login", json={"username": "Administrator", "password": "BOSSMAN"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    ADMIN_VALID_TOKEN = token


def test_league_creation(client: TestClient):

    response = client.post("/league_create", json={"name": "week1", "game": "greedy_pig"})
    assert response.status_code == 200
    print(response.json())
    assert "success" in response.json()["status"]

    response = client.post("/league_create")
    assert response.status_code == 422
    
    response = client.post("/league_create", json={"name": "", "game": "greedy_pig"})
    assert response.status_code == 200
    assert response.json() == {'status': 'failed', 'message': 'Name is Empty', 'data': None}

    response = client.post("/league_create", json={"name": "week2", "game": "greedy_pig"}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]


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
    

def test_toggle_league_active(client: TestClient):
    # Create a league
    league_name = "test_league"
    response = client.post("/league_create", json={"name": league_name, "game": "greedy_pig"}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200

    # Toggle league active status
    response = client.post("/toggle_league_active", json={"name": league_name}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["active"] == False

    # Toggle league active status again
    response = client.post("/toggle_league_active", json={"name": league_name},headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["message"] == f"League '{league_name}' active status toggled"
    assert response.json()["active"] == True

    # Try to toggle a non-existent league
    response = client.post("/toggle_league_active", json={"name": "non_existent_league"},headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "League 'non_existent_league' not found"

    # Toggle league active status without admin
    response = client.post("/toggle_league_active", json={"name": league_name})
    assert response.status_code == 401


def test_get_all_admin_leagues(client: TestClient):
    response = client.get("/get_all_admin_leagues")
    print(response.json())
    assert response.status_code == 200
    '''
    test for this:
    [{'expiry_date': '2024-06-10T19:42:48.135167', 'active': True, 'folder': 'leagues/admin/unassigned', 'game': 'greedy_pig', 'id': 1, 'created_date': '2024-06-03T07:42:48.135163', 'name': 'unassigned', 'deleted_date': None, 'signup_link': None}, {'expiry_date': '2024-06-10T19:42:48.135263', 'active': True, 'folder': 'leagues/admin/comp_test', 'game': 'greedy_pig', 'id': 2, 'created_date': '2024-06-03T07:42:48.135262', 'name': 'comp_test', 'deleted_date': None, 'signup_link': None}]
    '''
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "unassigned"
    assert response.json()[1]["name"] == "comp_test"
    assert response.json()[0]["active"] == True
    assert response.json()[1]["active"] == True
    assert response.json()[0]["game"] == "greedy_pig"
    assert response.json()[1]["game"] == "greedy_pig"
    assert response.json()[0]["folder"] == "leagues/admin/unassigned"
    assert response.json()[1]["folder"] == "leagues/admin/comp_test"

    