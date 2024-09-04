import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
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
    admin_login_response = client.post("/admin_login", json={"username": "Administrator", "password": "BOSSMAN"})
    assert admin_login_response.status_code == 200
    return admin_login_response.json()["data"]["access_token"]

def test_greedy_pig_simulation(client, admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200
    response_data = simulation_response.json()
    assert "data" in response_data
    assert "total_points" in response_data["data"]

def test_greedy_pig_simulation_with_custom_rewards(client, admin_token):
    custom_rewards = [15, 10, 5, 3, 2, 1]
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "custom_rewards": custom_rewards, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200
    response_data = simulation_response.json()
    assert "data" in response_data
    assert "total_points" in response_data["data"]
    assert "rewards" in response_data["data"]
    assert response_data["data"]["rewards"] == custom_rewards

def test_forty_two_simulation(client, admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "forty_two_test", "num_simulations": 100, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200
    response_data = simulation_response.json()
    assert "data" in response_data
    assert "total_points" in response_data["data"]

def test_forty_two_simulation_with_custom_rewards(client, admin_token):
    custom_rewards = [20, 15, 10, 5, 3, 2, 1]
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "forty_two_test", "num_simulations": 100, "custom_rewards": custom_rewards, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200
    response_data = simulation_response.json()
    assert "data" in response_data
    assert "total_points" in response_data["data"]
    assert "rewards" in response_data["data"]
    assert response_data["data"]["rewards"] == custom_rewards

def test_alpha_guess_simulation(client, admin_token):
    # Create a test league for Alpha Guess
    league_response = client.post(
        "/league_create",
        json={"name": "alpha_guess_test", "game": "alpha_guess"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert league_response.status_code == 200

    # Create and assign a test team
    team_response = client.post(
        "/team_create",
        json={"name": "alpha_guess_team", "password": "testpass", "school_name": "Test School"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert team_response.status_code == 200

    login_response = client.post("/team_login", json={"name": "alpha_guess_team", "password": "testpass"})
    assert login_response.status_code == 200
    team_token = login_response.json()["data"]["access_token"]

    assign_response = client.post(
        "/league_assign",
        json={"name": "alpha_guess_test"},
        headers={"Authorization": f"Bearer {team_token}"}
    )
    assert assign_response.status_code == 200

    # Submit a custom player for Alpha Guess
    code = """
from games.alpha_guess.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return random.choice('abcdefghijklmnopqrstuvwxyz')
"""
    submission_response = client.post(
        "/submit_agent",
        json={"code": code},
        headers={"Authorization": f"Bearer {team_token}"}
    )
    assert submission_response.status_code == 200

    # Run the simulation
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "alpha_guess_test", "num_simulations": 100, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200
    response_data = simulation_response.json()
    assert "data" in response_data
    assert "total_points" in response_data["data"]
    assert "alpha_guess_team" in response_data["data"]["total_points"]
    assert 0 <= response_data["data"]["total_points"]["alpha_guess_team"] <= 10000

    # Clean up
    client.post("/delete_team", json={"name": "alpha_guess_team"}, headers={"Authorization": f"Bearer {admin_token}"})

# Note: Alpha Guess doesn't use custom rewards, so we don't need a separate test for that