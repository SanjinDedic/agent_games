import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from games.forty_two.forty_two import FortyTwoGame
from games.greedy_pig.greedy_pig import GreedyPigGame
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

@pytest.fixture(scope="module")
def non_admin_token(client):
    non_admin_token = client.post("/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"}).json()["data"]["access_token"]
    return non_admin_token

def test_alpha_guess_submission_and_simulation(client, db_session, admin_token):
    # Create a test league for Alpha Guess
    league_response = client.post(
        "/league_create",
        json={"name": "alpha_guess_test", "game": "alpha_guess"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert league_response.status_code == 200
    assert league_response.json()["status"] == "success"

    # Create a test team
    team_response = client.post(
        "/team_create",
        json={"name": "alpha_guess_team", "password": "testpass", "school_name": "Test School"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert team_response.status_code == 200
    assert team_response.json()["status"] == "success"

    # Login as the test team
    login_response = client.post(
        "/team_login",
        json={"name": "alpha_guess_team", "password": "testpass"}
    )
    assert login_response.status_code == 200
    team_token = login_response.json()["data"]["access_token"]

    # Assign the team to the league
    assign_response = client.post(
        "/league_assign",
        json={"name": "alpha_guess_test"},
        headers={"Authorization": f"Bearer {team_token}"}
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["status"] == "success"

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
    print(f"Submission response for validation SIM: {submission_response.json()}")
    assert submission_response.status_code == 200
    assert "Code submitted successfully" in submission_response.json()["message"]

    # Run a simulation for the Alpha Guess test league
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "alpha_guess_test", "num_simulations": 100, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200

    response_data = simulation_response.json()
    print("Alpha Guess Simulation Response:", response_data)

    assert "data" in response_data
    assert response_data["data"] is not None
    assert "total_points" in response_data["data"]
    assert "alpha_guess_team" in response_data["data"]["total_points"]
    assert 0 <= response_data["data"]["total_points"]["alpha_guess_team"] <= 10000

    # Clean up: Delete the test team and league
    client.post("/delete_team", json={"name": "alpha_guess_team"}, headers={"Authorization": f"Bearer {admin_token}"})
    # Note: There's no endpoint to delete a league, so it will remain in the database

def test_run_simulation(client, db_session, admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200

    response_data = simulation_response.json()
    print("Simulation Response:", response_data)

    assert "data" in response_data, "Response does not contain 'data' key"
    assert response_data["data"] is not None, "Response 'data' is None"
    assert "total_points" in response_data["data"], "Response data does not contain 'total_points'"
    assert isinstance(response_data["data"]["total_points"], dict)
    assert len(response_data["data"]["total_points"]) > 0


def test_get_published_results_for_all_leagues(client, db_session, admin_token):
    # Test getting published results for all leagues
    response = client.get("/get_published_results_for_all_leagues")
    print("ALL PUBLISHED",response.json())
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert len(response.json()["data"]) == 1

def test_run_forty_two_simulation(client, admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "forty_two_test", "num_simulations": 100},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    print("SIMULATION RESPONSE",simulation_response.json())
    assert simulation_response.status_code == 200
    assert "total_points" in simulation_response.json()["data"]

def test_run_simulation_with_custom_rewards(client, admin_token):
    custom_rewards = [15, 10, 5, 3, 2, 1]
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "custom_rewards": custom_rewards},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200

    response_data = simulation_response.json()
    print("Simulation Response:", response_data)

    assert "data" in response_data
    assert response_data["data"] is not None
    assert "total_points" in response_data["data"]
    assert "rewards" in response_data["data"]
    assert response_data["data"]["rewards"] == str(custom_rewards)

def test_run_simulation_with_default_rewards(client, admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200

    response_data = simulation_response.json()
    print("Simulation Response:", response_data)

    assert "data" in response_data
    assert response_data["data"] is not None
    assert "total_points" in response_data["data"]
    assert "rewards" in response_data["data"]

#####   RUN SIMULATION WITH INVALID REWARDS  #####


def test_run_simulation_with_invalid_custom_rewards(client, admin_token):
    invalid_custom_rewards = [10, 5, "invalid", 2, 1]
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "custom_rewards": invalid_custom_rewards},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 422  # Unprocessable Entity

#####   RUN SIMULATION WITH EMPTY REWARDS  #####


def test_run_simulation_with_empty_custom_rewards(client, admin_token):
    empty_custom_rewards = []
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "custom_rewards": empty_custom_rewards},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200

    response_data = simulation_response.json()
    print("Simulation Response:", response_data)

    assert "data" in response_data
    assert response_data["data"] is not None
    assert "total_points" in response_data["data"]
    assert "rewards" in response_data["data"]
    assert response_data["data"]["rewards"] == '[]'

def test_run_greedy_pig_simulation_with_custom_rewards(client, admin_token):
    custom_rewards = [20, 15, 10, 5, 3, 2, 1]
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "custom_rewards": custom_rewards},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200

    response_data = simulation_response.json()
    print("Simulation Response:", response_data)

    assert "data" in response_data
    assert response_data["data"] is not None
    assert "total_points" in response_data["data"]
    assert "rewards" in response_data["data"]
    assert response_data["data"]["rewards"] == str(custom_rewards)

def test_run_forty_two_simulation_with_custom_rewards(client, admin_token):
    custom_rewards = [20, 15, 10, 5, 3, 2, 1]
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "forty_two_test", "num_simulations": 100, "custom_rewards": custom_rewards},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200

    response_data = simulation_response.json()
    print("Simulation Response:", response_data)

    assert "data" in response_data
    assert response_data["data"] is not None
    assert "total_points" in response_data["data"]
    assert "rewards" in response_data["data"]
    assert response_data["data"]["rewards"] == str(custom_rewards)

def test_custom_rewards_consistency(client, admin_token):
    custom_rewards = [15, 10, 5, 3, 2, 1]
    simulation_response1 = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "custom_rewards": custom_rewards},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    simulation_response2 = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "custom_rewards": custom_rewards},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert simulation_response1.status_code == 200
    assert simulation_response2.status_code == 200

    response_data1 = simulation_response1.json()
    response_data2 = simulation_response2.json()

    assert response_data1["data"]["rewards"] == str(custom_rewards)
    assert response_data2["data"]["rewards"] == str(custom_rewards)
    assert response_data1["data"]["rewards"] == response_data2["data"]["rewards"]

def test_run_simulation_without_docker(client, db_session, admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200

    response_data = simulation_response.json()
    print("Simulation Response:", response_data)

    assert "data" in response_data
    assert response_data["data"] is not None
    assert "total_points" in response_data["data"]
    assert isinstance(response_data["data"]["total_points"], dict)
    assert len(response_data["data"]["total_points"]) > 0

def test_run_forty_two_simulation_without_docker(client, admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "forty_two_test", "num_simulations": 100, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    print("SIMULATION RESPONSE", simulation_response.json())
    assert simulation_response.status_code == 200
    assert "total_points" in simulation_response.json()["data"]

def test_run_simulation_with_custom_rewards_without_docker(client, admin_token):
    custom_rewards = [15, 10, 5, 3, 2, 1]
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "custom_rewards": custom_rewards, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200

    response_data = simulation_response.json()
    print("Simulation Response:", response_data)

    assert "data" in response_data
    assert response_data["data"] is not None
    assert "total_points" in response_data["data"]
    assert "rewards" in response_data["data"]
    assert response_data["data"]["rewards"] == str(custom_rewards)

def test_compare_docker_and_non_docker_simulations(client, admin_token):
    docker_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "use_docker": True},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    non_docker_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert docker_response.status_code == 200
    assert non_docker_response.status_code == 200

    docker_data = docker_response.json()["data"]
    non_docker_data = non_docker_response.json()["data"]

    assert set(docker_data["total_points"].keys()) == set(non_docker_data["total_points"].keys())
    assert docker_data["num_simulations"] == non_docker_data["num_simulations"]

    # Check for feedback in Docker response
    assert "feedback" in docker_data
    assert isinstance(docker_data["feedback"], str)
    assert len(docker_data["feedback"]) > 0

    # Non-Docker response should not have feedback
    assert "feedback" not in non_docker_data