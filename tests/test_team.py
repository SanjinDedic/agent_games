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