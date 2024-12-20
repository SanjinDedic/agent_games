import os

import pytest
from api import app
from database import create_administrator, get_db_engine
from fastapi.testclient import TestClient
from models_db import Admin
from sqlmodel import Session, select
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
    login_response = client.post(
        "/admin_login", json={"username": "Administrator", "password": "BOSSMAN"}
    )
    assert login_response.status_code == 200
    return login_response.json()["data"]["access_token"]


def test_team_login(client):
    response = client.post(
        "/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "access_token" in response.json()["data"]

    response = client.post(
        "/team_login", json={"name": "BrunswickSC1", "password": "wrongpass"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "Invalid team password"

    response = client.post(
        "/team_login", json={"name": "NonExistentTeam", "password": "somepass"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "Team 'NonExistentTeam' not found"


def test_successful_admin_login(client):
    login_response = client.post(
        "/admin_login", json={"username": "Administrator", "password": "BOSSMAN"}
    )
    assert login_response.status_code == 200
    assert login_response.json()["status"] == "success"
    assert "access_token" in login_response.json()["data"]


def test_admin_login_missing_fields(client):
    login_response = client.post("/admin_login", json={"username": "Administrator"})
    assert login_response.status_code == 422

    login_response = client.post("/admin_login", json={"password": "BOSSMAN"})
    assert login_response.status_code == 422


def test_create_administrator(db_session):
    result = create_administrator(db_session, "admin", "password123")
    assert result == {
        "status": "success",
        "message": "Admin 'admin' created successfully",
    }

    administrator = db_session.exec(
        select(Admin).where(Admin.username == "admin")
    ).one_or_none()
    assert administrator is not None
    assert administrator.username == "admin"


def test_create_administrator_missing_fields(db_session):
    result = create_administrator(db_session, "admin2", "")
    assert result == {
        "status": "failed",
        "message": "Username and password are required",
    }

    administrator = db_session.exec(
        select(Admin).where(Admin.username == "admin2")
    ).one_or_none()
    assert administrator is None


def test_create_administrator_duplicate(db_session):
    create_administrator(db_session, "Administrator", "BOSSMAN")
    result = create_administrator(db_session, "Administrator", "BOSSMAN")
    assert result == {
        "status": "failed",
        "message": "Admin with username 'Administrator' already exists",
    }


def test_admin_login_exception(client, mocker):
    # Mock the get_admin_token function to raise an exception
    mocker.patch(
        "database.get_admin_token", side_effect=Exception("Database connection error")
    )

    login_response = client.post(
        "/admin_login", json={"username": "Administrator", "password": "BOSSMAN"}
    )
    assert login_response.status_code == 200
    assert login_response.json() == {
        "status": "failed",
        "message": "Database connection error",
        "data": None,
    }


def test_run_simulation_with_nonexistent_league(client, admin_token):
    response = client.post(
        "/run_simulation",
        json={"league_name": "non_existent_league", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "League 'non_existent_league' not found" in response.json()["message"]


def test_run_simulation_without_docker(client, admin_token):
    response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "total_points" in response.json()["data"]
    assert (
        "feedback" not in response.json()["data"]
    )  # Feedback is not included when not using Docker
