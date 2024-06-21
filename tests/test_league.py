import os
import sys
import pytest
import shutil
from fastapi.testclient import TestClient
from sqlmodel import Session

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from models_db import League
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
    login_response = client.post("/admin_login", json={"username": "Administrator", "password": "BOSSMAN"})
    assert login_response.status_code == 200
    return login_response.json()["data"]["access_token"]

@pytest.fixture(scope="module")
def user_token(client, admin_token):
    team_name = "BrunswickSC1"
    team_login_response = client.post(
        "/team_login", json={"name": f"{team_name}", "password": "ighEMkOP"}, headers={"Authorization": f"Bearer {admin_token}"})
    assert team_login_response.status_code == 200
    return team_login_response.json()["data"]["access_token"]

def test_league_creation(client, admin_token):
    response = client.post("/league_create", json={"name": "week1", "game": "greedy_pig"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]

    response = client.post("/league_create")
    assert response.status_code == 422
    
    response = client.post("/league_create", json={"name": "", "game": "greedy_pig"})
    assert response.status_code == 200
    assert response.json() == {'status': 'failed', 'message': 'Name is Empty', 'data': None}

    response = client.post("/league_create", json={"name": "week2", "game": "greedy_pig"}, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]

def test_league_join(client):
    response = client.post("/league_join/MQ%3D%3D", json={"name": "std", "password": "pass", "school": "abc"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_league_folder_creation(client, admin_token):
    league_name = "test_league_admin"
    response = client.post("/league_create", json={"name": league_name, "game": "greedy_pig"}, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]
    assert os.path.isdir(f"games/greedy_pig/leagues/admin/{league_name}")
    shutil.rmtree(f"games/greedy_pig/leagues/admin/{league_name}")
    assert not os.path.isdir(f"games/greedy_pig/leagues/user/{league_name}")

def test_league_folder_creation_no_auth(client):
    league_name = "test_league_user"
    response = client.post("/league_create", json={"name": league_name, "game": "greedy_pig"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]
    assert os.path.isdir(f"games/greedy_pig/leagues/user/{league_name}")
    shutil.rmtree(f"games/greedy_pig/leagues/user/{league_name}")
    assert not os.path.isdir(f"games/greedy_pig/leagues/user/{league_name}")


def test_get_all_admin_leagues(client):
    response = client.get("/get_all_admin_leagues")
    assert response.status_code == 200
    assert len(response.json()) == 3
    assert response.json()["data"]["admin_leagues"][0]["name"] == "unassigned"
    assert response.json()["data"]["admin_leagues"][1]["name"] == "comp_test"
    assert response.json()["data"]["admin_leagues"][0]["game"] == "greedy_pig"
    assert response.json()["data"]["admin_leagues"][1]["game"] == "greedy_pig"
    assert response.json()["data"]["admin_leagues"][0]["folder"] == "leagues/admin/unassigned"
    assert response.json()["data"]["admin_leagues"][1]["folder"] == "leagues/admin/comp_test"

def test_update_expiry_date(client, admin_token):
    league_name = "unassigned"
    date = "2024-06-10T19:42:48.135167"
    response = client.post("/update_expiry_date", json={"date": f"{date}", "league": f"{league_name}"}, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["message"] == f"Expiry date for league '{league_name}' updated successfully"

def test_update_expiry_date_user_token(client, user_token):
    league_name = "unassigned"
    date = "2024-06-10T19:42:48.135167"
    response = client.post("/update_expiry_date", json={"date": f"{date}", "league": f"{league_name}"}, headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "Only admin users can update the expiry date"

def test_update_expiry_date_not_existing(client, admin_token):
    league_name = "dont exist"
    date = "2024-06-10T19:42:48.135167"
    response = client.post("/update_expiry_date", json={"date": f"{date}", "league": f"{league_name}"}, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "League 'dont exist' not found"

def test_update_expiry_date_invalid_token(client):
    date = "2024-06-10T19:42:48.135167"
    league_name = "unassigned"
    response = client.post("/update_expiry_date", json={"name": league_name, "game": "greedy_pig"}, headers={"Authorization": f"Bearer dsfdsfds"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_league_creation_exception(client, admin_token, monkeypatch):
    
    def mock_create_league(*args, **kwargs):
        raise Exception("Database error")

    monkeypatch.setattr("api.create_league", mock_create_league)

    response = client.post("/league_create", 
                           json={"name": "exception_league", "game": "greedy_pig"},
                           headers={"Authorization": f"Bearer {admin_token}"})
    
    assert response.status_code == 200
    print(response.json())
    assert response.json() == {
        "status": "failed",
        "message": "Database error",
        "data": None
    }