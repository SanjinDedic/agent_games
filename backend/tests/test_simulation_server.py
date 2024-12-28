import os
from datetime import datetime, timedelta

import pytest
from api import app
from database import get_db_engine
from fastapi.testclient import TestClient
from models_db import League
from sqlmodel import Session
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


@pytest.fixture
def test_league():
    return League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=1),
        folder="test_folder",
        game="greedy_pig",
    )


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "running" in response.json()["message"]
    assert "success" in response.json()["status"]


def test_simulate_success(client, admin_token):
    response = client.post(
        "/run_simulation",
        json={
            "league_name": "comp_test",
            "league_game": "greedy_pig",
            "num_simulations": 10,
            "custom_rewards": [10, 8, 6, 4, 2, 1],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "total_points" in data["data"]
    assert "num_simulations" in data["data"]
    assert "table" in data["data"]
    assert data["data"]["num_simulations"] == 10


def test_simulate_with_player_feedback(client, admin_token):
    response = client.post(
        "/run_simulation",
        json={
            "league_name": "comp_test",
            "league_game": "greedy_pig",
            "num_simulations": 5,
            "player_feedback": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "feedback" in data["data"]
    assert "player_feedback" in data["data"]


def test_simulate_invalid_league(client, admin_token):
    response = client.post(
        "/run_simulation",
        json={
            "league_name": "nonexistent_league",
            "league_game": "greedy_pig",
            "num_simulations": 10,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "League 'nonexistent_league' not found" in data["message"]


def test_simulate_unauthorized(client):
    response = client.post(
        "/run_simulation",
        json={
            "league_name": "comp_test",
            "league_game": "greedy_pig",
            "num_simulations": 10,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_simulate_invalid_token(client):
    response = client.post(
        "/run_simulation",
        json={
            "league_name": "comp_test",
            "league_game": "greedy_pig",
            "num_simulations": 10,
        },
        headers={"Authorization": "Bearer invalid_token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_simulate_non_admin_user(client, db_session):
    # Create and login as a non-admin user
    team_token_response = client.post(
        "/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"}
    )
    assert team_token_response.status_code == 200
    team_token = team_token_response.json()["data"]["access_token"]

    response = client.post(
        "/run_simulation",
        json={
            "league_name": "comp_test",
            "league_game": "greedy_pig",
            "num_simulations": 10,
        },
        headers={"Authorization": f"Bearer {team_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "Only admin users can run simulations" in data["message"]


def test_simulate_with_custom_rewards(client, admin_token):
    custom_rewards = [15, 12, 9, 6, 3, 1]
    response = client.post(
        "/run_simulation",
        json={
            "league_name": "comp_test",
            "league_game": "greedy_pig",
            "num_simulations": 10,
            "custom_rewards": custom_rewards,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "rewards" in data["data"]
    assert data["data"]["rewards"] == custom_rewards


if __name__ == "__main__":
    pytest.main(["-v", __file__])
