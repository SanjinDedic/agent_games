import os
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch

import database
import pytest
from api import app
from config import ROOT_DIR
from database import get_db_engine
from fastapi.testclient import TestClient
from models_db import League, SimulationResult
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


@pytest.fixture(scope="module")
def user_token(client, admin_token):
    team_name = "BrunswickSC1"
    team_login_response = client.post(
        "/team_login",
        json={"name": f"{team_name}", "password": "ighEMkOP"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert team_login_response.status_code == 200
    return team_login_response.json()["data"]["access_token"]


@pytest.fixture(scope="module")
def non_admin_token(client, admin_token):
    # Create a non-admin user and get their token
    team_name = "TestTeam"
    team_password = "testpassword"

    # First, create the team using the admin token
    create_response = client.post(
        "/team_create",
        json={
            "name": team_name,
            "password": team_password,
            "school_name": "Test School",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    print(f"Team creation response: {create_response.status_code}")
    print(f"Team creation response content: {create_response.json()}")
    assert (
        create_response.status_code == 200
    ), f"Failed to create team: {create_response.json()}"

    # Then, log in as this team to get the token
    login_response = client.post(
        "/team_login", json={"name": team_name, "password": team_password}
    )
    print(f"Login response: {login_response.status_code}")
    print(f"Login response content: {login_response.json()}")
    assert (
        login_response.status_code == 200
    ), f"Failed to log in: {login_response.json()}"

    response_data = login_response.json()
    assert "data" in response_data, f"Unexpected response structure: {response_data}"
    assert (
        "access_token" in response_data["data"]
    ), f"No access token in response: {response_data}"

    return response_data["data"]["access_token"]


def test_league_creation(client, admin_token):
    response = client.post(
        "/league_create",
        json={"name": "week1", "game": "greedy_pig"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert "success" in response.json()["status"]

    response = client.post("/league_create")
    assert response.status_code == 401

    response = client.post(
        "/league_create",
        json={"name": "", "game": "greedy_pig"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "status": "failed",
        "message": "Name is Empty",
        "data": None,
    }

    response = client.post(
        "/league_create",
        json={"name": "week2", "game": "greedy_pig"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert "success" in response.json()["status"]


def test_league_folder_creation(client, admin_token):
    league_name = "test_league_admin"
    response = client.post(
        "/league_create",
        json={"name": league_name, "game": "greedy_pig"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert "success" in response.json()["status"]

    expected_folder = os.path.join(
        ROOT_DIR, "games", "greedy_pig", "leagues", "admin", league_name
    )
    print(f"Expected folder path: {expected_folder}")
    assert os.path.isdir(expected_folder)

    # Clean up: remove the created folder
    if os.path.exists(expected_folder):
        shutil.rmtree(expected_folder)


def test_league_folder_creation_no_auth(client):
    league_name = "test_league_user"
    response = client.post(
        "/league_create", json={"name": league_name, "game": "greedy_pig"}
    )
    assert response.status_code == 401
    print(response.json())


def test_get_all_admin_leagues(client):
    response = client.get("/get_all_admin_leagues")
    assert response.status_code == 200
    assert len(response.json()) == 3
    assert response.json()["data"]["admin_leagues"][0]["name"] == "unassigned"
    assert response.json()["data"]["admin_leagues"][1]["name"] == "comp_test"
    assert response.json()["data"]["admin_leagues"][0]["game"] == "greedy_pig"
    assert response.json()["data"]["admin_leagues"][1]["game"] == "greedy_pig"
    assert (
        response.json()["data"]["admin_leagues"][0]["folder"]
        == "leagues/admin/unassigned"
    )
    assert (
        response.json()["data"]["admin_leagues"][1]["folder"]
        == "leagues/admin/comp_test"
    )


def test_update_expiry_date_user_token(client, user_token):
    league_name = "unassigned"
    date = "2024-06-10T19:42:48.135167"
    response = client.post(
        "/update_expiry_date",
        json={"date": f"{date}", "league": f"{league_name}"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "Only admin users can update the expiry date"


def test_update_expiry_date_not_existing(client, admin_token):
    league_name = "dont exist"
    date = "2024-06-10T19:42:48.135167"
    response = client.post(
        "/update_expiry_date",
        json={"date": f"{date}", "league": f"{league_name}"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "League 'dont exist' not found"


def test_update_expiry_date_invalid_token(client):
    league_name = "unassigned"
    response = client.post(
        "/update_expiry_date",
        json={"name": league_name, "game": "greedy_pig"},
        headers={"Authorization": "Bearer dsfdsfds"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_league_creation_exception(client, admin_token, monkeypatch):

    def mock_create_league(*args, **kwargs):
        raise Exception("Database error")

    monkeypatch.setattr("database.create_league", mock_create_league)

    response = client.post(
        "/league_create",
        json={"name": "exception_league", "game": "greedy_pig"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    print(response.json())
    assert response.json() == {
        "status": "failed",
        "message": "Database error",
        "data": None,
    }


def test_get_all_league_results(client, admin_token, non_admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response.status_code == 200
    # print("SIM RESPONSE FOR GET ALL LEAGUE RES:", simulation_response.json())

    league_results_response = client.post(
        "/get_all_league_results",
        json={"name": "comp_test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert league_results_response.status_code == 200
    response_data = league_results_response.json()

    # Check if the response contains an error message
    if response_data.get("status") == "error":
        print(f"API returned an error: {response_data.get('message')}")
        assert False, f"API returned an error: {response_data.get('message')}"

    # If no error, proceed with the original assertions
    assert "data" in response_data
    assert "all_results" in response_data["data"]
    assert isinstance(response_data["data"]["all_results"], list)

    # Add more specific assertions about the content of all_results if needed

    # Test unauthorized access
    unauthorized_response = client.post(
        "/get_all_league_results",
        json={"name": "comp_test"},
        headers={"Authorization": f"Bearer {non_admin_token}"},
    )
    assert (
        unauthorized_response.json()["message"]
        == "Only admin users can view league results"
    )


def test_publish_results(client, db_session, admin_token, non_admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response.status_code == 200
    simulation_id = simulation_response.json()["data"]["id"]

    publish_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "success"
    assert (
        publish_response.json()["message"]
        == "Simulation results for league 'comp_test' published successfully"
    )

    simulation_result = db_session.exec(
        select(SimulationResult).where(SimulationResult.id == simulation_id)
    ).one()
    assert simulation_result.published is True

    publish_again_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_again_response.status_code == 200
    assert publish_again_response.json()["status"] == "success"
    assert (
        publish_again_response.json()["message"]
        == "Simulation results for league 'comp_test' published successfully"
    )

    simulation_result = db_session.exec(
        select(SimulationResult).where(SimulationResult.id == simulation_id)
    ).one()
    assert simulation_result.published is True

    unauthorized_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {non_admin_token}"},
    )
    assert (
        unauthorized_response.json()["message"]
        == "Only admin users can publish league results"
    )

    simulation_result = db_session.exec(
        select(SimulationResult).where(SimulationResult.id == simulation_id)
    ).one()
    assert simulation_result.published is True


def test_publish_one_simulation_per_league(client, db_session, admin_token):
    simulation_response1 = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response1.status_code == 200
    simulation_id1 = simulation_response1.json()["data"]["id"]

    publish_response1 = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response1.status_code == 200
    assert publish_response1.json()["status"] == "success"
    assert (
        publish_response1.json()["message"]
        == "Simulation results for league 'comp_test' published successfully"
    )

    simulation_response2 = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response2.status_code == 200
    simulation_id2 = simulation_response2.json()["data"]["id"]

    publish_response2 = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response2.status_code == 200
    assert publish_response2.json()["status"] == "success"

    simulation_result1 = db_session.exec(
        select(SimulationResult).where(SimulationResult.id == simulation_id1)
    ).one()
    assert simulation_result1.published is False

    simulation_result2 = db_session.exec(
        select(SimulationResult).where(SimulationResult.id == simulation_id2)
    ).one()
    assert simulation_result2.published is True


def test_get_published_results_for_league(client, db_session, admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response.status_code == 200
    simulation_id = simulation_response.json()["data"]["id"]

    publish_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "success"
    assert (
        publish_response.json()["message"]
        == "Simulation results for league 'comp_test' published successfully"
    )

    get_published_response = client.post(
        "/get_published_results_for_league", json={"name": "comp_test"}
    )
    assert get_published_response.status_code == 200
    simulation_result = db_session.exec(
        select(SimulationResult).where(SimulationResult.id == simulation_id)
    ).one()
    assert simulation_result.published is True


def test_get_published_result(client, db_session, admin_token):
    # First, run a simulation and publish the results
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response.status_code == 200
    simulation_id = simulation_response.json()["data"]["id"]

    publish_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response.status_code == 200

    # Now test getting the published result
    response = client.post(
        "/get_published_results_for_league", json={"name": "comp_test"}
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result is not None
    assert "league_name" in result
    assert "total_points" in result
    assert "table" in result
    assert "num_simulations" in result
    assert "active" in result
    assert "rewards" in result

    # Test getting published result for a non-existent league
    response = client.post(
        "/get_published_results_for_league", json={"name": "non_existent_league"}
    )
    assert response.status_code == 200
    assert response.json()["data"] is None


def test_update_expiry_date(client, db_session, admin_token):
    league_name = "comp_test"
    new_expiry_date = datetime.now() + timedelta(days=30)

    response = client.post(
        "/update_expiry_date",
        json={"date": new_expiry_date.isoformat(), "league": league_name},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert (
        f"Expiry date for league '{league_name}' updated successfully"
        in response.json()["message"]
    )

    # Verify the update in the database
    league = database.get_league(db_session, league_name)
    assert abs(league.expiry_date - new_expiry_date) < timedelta(seconds=1)

    # Test updating expiry date for a non-existent league
    non_existent_league = "non_existent_league"
    response = client.post(
        "/update_expiry_date",
        json={"date": new_expiry_date.isoformat(), "league": non_existent_league},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert f"League '{non_existent_league}' not found" in response.json()["message"]


def test_get_published_result_with_nonexistent_league(client, db_session):
    response = client.post(
        "/get_published_results_for_league", json={"name": "non_existent_league"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "League 'non_existent_league' not found" in response.json()["message"]


def test_get_all_published_results_with_no_results(client, db_session):
    # First, ensure no results are published
    leagues = db_session.exec(select(League)).all()
    for league in leagues:
        for sim in league.simulation_results:
            sim.published = False
    db_session.commit()

    response = client.get("/get_published_results_for_all_leagues")
    assert response.status_code == 200
    print("No results league:", response.json())
    assert response.json()["status"] == "success"
    assert response.json()["message"] == "Published results retrieved successfully"
    assert response.json()["data"] == {"all_results": []}


def test_get_available_games(client):
    response = client.post("/get_available_games")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "games" in response.json()["data"]
    assert isinstance(response.json()["data"]["games"], list)
    assert len(response.json()["data"]["games"]) > 0


@patch("api.get_games_names")
def test_get_available_games_exception(mock_get_games_names, client):
    mock_get_games_names.side_effect = Exception("Test exception")
    response = client.post("/get_available_games")
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "An error occurred" in response.json()["message"]
    assert "Test exception" in response.json()["message"]


def test_get_published_results_for_all_leagues(client, db_session, admin_token):
    # First, create some test data
    league_name = "comp_test"
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": league_name, "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response.status_code == 200
    simulation_id = simulation_response.json()["data"]["id"]

    # Publish the results
    publish_response = client.post(
        "/publish_results",
        json={"league_name": league_name, "id": simulation_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response.status_code == 200

    # Now test the get_published_results_for_all_leagues endpoint
    response = client.get("/get_published_results_for_all_leagues")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "all_results" in response.json()["data"]
    assert len(response.json()["data"]["all_results"]) > 0


def test_get_published_results_for_all_leagues_no_results(client, db_session):
    # Mock the database function to return an empty list
    with patch("database.get_all_published_results") as mock_get_results:
        mock_get_results.return_value = {"all_results": []}

        response = client.get("/get_published_results_for_all_leagues")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["message"] == "Published results retrieved successfully"
        assert response.json()["data"]["all_results"] == []


@patch("database.get_all_published_results")
def test_get_published_results_for_all_leagues_exception(
    mock_get_all_published_results, client
):
    mock_get_all_published_results.side_effect = Exception("Test exception")
    response = client.get("/get_published_results_for_all_leagues")
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert (
        "An error occurred while retrieving published results"
        in response.json()["message"]
    )
