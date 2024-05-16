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

@pytest.fixture(scope="session")
def db_engine():
    engine = setup_test_db(verbose=True)
    yield engine
    if os.path.exists("../test.db"):
        os.remove("../test.db")
    else:
        os.remove("test.db")
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

    response = client.post("/league_create", json={"name": "week1"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]

    response = client.post("/league_create")
    assert response.status_code == 422
    
    response = client.post("/league_create", json={"name": ""})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Name is Empty"}

    response = client.post("/league_create", json={"name": "week2"}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]

def test_league_join(client: TestClient):

    response = client.post("/league_join/MQ%3D%3D", json={"name": "std", "password": "pass", "school": "abc"})
    assert response.status_code == 200
    assert "access_token" in response.json()
