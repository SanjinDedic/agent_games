import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import create_administrator, get_db_engine
from models_db import Admin, League
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

def test_team_login(client):
    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "access_token" in response.json()["data"]

    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "wrongpass"})
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "Invalid team password"

    response = client.post("/team_login", json={"name": "NonExistentTeam", "password": "somepass"})
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "Team 'NonExistentTeam' not found"

def test_successful_admin_login(client):
    login_response = client.post("/admin_login", json={"username": "Administrator", "password": "BOSSMAN"})
    assert login_response.status_code == 200
    assert login_response.json()["status"] == "success"
    assert "access_token" in login_response.json()["data"]

def test_admin_login_missing_fields(client):
    login_response = client.post("/admin_login", json={"username": "Administrator"})
    assert login_response.status_code == 422

    login_response = client.post("/admin_login", json={"password": "BOSSMAN"})
    assert login_response.status_code == 422

def test_create_administrator(db_session):
    result = create_administrator(db_session, 'admin', 'password123')
    assert result == {"status": "success", "message": "Admin 'admin' created successfully"}
    
    administrator = db_session.exec(select(Admin).where(Admin.username == 'admin')).one_or_none()
    assert administrator is not None
    assert administrator.username == 'admin'

def test_create_administrator_missing_fields(db_session):
    result = create_administrator(db_session, 'admin2', '')
    assert result == {"status": "failed", "message": "Username and password are required"}
    
    administrator = db_session.exec(select(Admin).where(Admin.username == 'admin2')).one_or_none()
    assert administrator is None

def test_create_administrator_duplicate(db_session):
    create_administrator(db_session, 'Administrator', 'BOSSMAN')
    result = create_administrator(db_session, 'Administrator', 'BOSSMAN')
    assert result == {"status": "failed", "message": "Admin with username 'Administrator' already exists"}