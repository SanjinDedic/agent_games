import os

import pytest
from api import app
from database import get_db_engine
from fastapi.testclient import TestClient
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
    admin_login_response = client.post(
        "/admin_login", json={"username": "Administrator", "password": "BOSSMAN"}
    )
    assert admin_login_response.status_code == 200
    return admin_login_response.json()["data"]["access_token"]


def test_greedy_pig_simulation(client, admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response.status_code == 200
    response_data = simulation_response.json()
    assert "data" in response_data
    assert "total_points" in response_data["data"]


def test_greedy_pig_simulation_with_custom_rewards(client, admin_token):
    custom_rewards = [15, 10, 5, 3, 2, 1]
    simulation_response = client.post(
        "/run_simulation",
        json={
            "league_name": "comp_test",
            "num_simulations": 100,
            "custom_rewards": custom_rewards,
            "use_docker": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response.status_code == 200
    response_data = simulation_response.json()
    assert "data" in response_data
    assert "total_points" in response_data["data"]
    assert "rewards" in response_data["data"]
    assert response_data["data"]["rewards"] == custom_rewards
