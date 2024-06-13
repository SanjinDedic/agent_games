import os
import sys
import pytest
import time
from fastapi.testclient import TestClient
from sqlmodel import Session, select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from models_db import League, SimulationResult
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

def test_admin_login(client: TestClient):
    global ADMIN_TOKEN
    # Get the token for the admin
    admin_login_response = client.post("/admin_login", json={"username": "Administrator", "password": "BOSSMAN"})
    assert admin_login_response.status_code == 200
    ADMIN_TOKEN = admin_login_response.json()["access_token"]
    assert ADMIN_TOKEN != ""

def test_run_simulation(client: TestClient, db_session: Session):
    global ADMIN_TOKEN
    print("ADMIN_TOKEN", ADMIN_TOKEN, "simulation called")
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert simulation_response.status_code == 200
    print("This is the simulation response", simulation_response.json())
    assert "total_points" in simulation_response.json()

    # Check if the simulation results are logged in the database
    simulation_results = db_session.exec(select(SimulationResult)).all()
    assert len(simulation_results) > 0

def test_get_all_league_results(client: TestClient):
    global ADMIN_TOKEN
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert simulation_response.status_code == 200
    league_results_response = client.post(
        "/get_all_league_results",
        json={"name": "comp_test"},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
)
    print("Version 1")
    print(league_results_response.json())
    assert league_results_response.status_code == 200
    assert isinstance(league_results_response.json(), list)


    # Test with non-admin user
    non_admin_token = client.post("/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"}).json()["access_token"]
    unauthorized_response = client.post(
        "/get_all_league_results",
        json={"name": "comp_test"},
        headers={"Authorization": f"Bearer {non_admin_token}"}
    )
    assert unauthorized_response.status_code == 403
    assert unauthorized_response.json()["detail"] == "Only admin users can view league results"

def test_publish_results(client: TestClient, db_session: Session):
    global ADMIN_TOKEN
    # Run a simulation
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert simulation_response.status_code == 200
    simulation_id = simulation_response.json()["simulation_id"]

    # Publish the simulation results
    publish_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "success"
    assert publish_response.json()["message"] == "Results published successfully"

    # Check if the simulation results are marked as published in the database
    simulation_result = db_session.exec(select(SimulationResult).where(SimulationResult.id == simulation_id)).one()
    assert simulation_result.published == True

    # Try publishing the same results again as an admin
    publish_again_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert publish_again_response.status_code == 200
    assert publish_again_response.json()["status"] == "success"
    assert publish_again_response.json()["message"] == "Results published successfully"

    # Check if the simulation results are still marked as published in the database
    simulation_result = db_session.exec(select(SimulationResult).where(SimulationResult.id == simulation_id)).one()
    assert simulation_result.published == True

    # Test with non-admin user
    non_admin_token = client.post("/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"}).json()["access_token"]
    unauthorized_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {non_admin_token}"}
    )
    assert unauthorized_response.status_code == 403
    assert unauthorized_response.json()["detail"] == "Only admin users can publish league results"

    # Check if the simulation results are still marked as published in the database
    simulation_result = db_session.exec(select(SimulationResult).where(SimulationResult.id == simulation_id)).one()
    assert simulation_result.published == True


def test_publish_one_simulation_per_league(client: TestClient, db_session: Session):
    global ADMIN_TOKEN
    # Run the first simulation
    simulation_response1 = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert simulation_response1.status_code == 200
    simulation_id1 = simulation_response1.json()["simulation_id"]

    # Publish the first simulation results
    publish_response1 = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id1},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert publish_response1.status_code == 200
    assert publish_response1.json()["status"] == "success"
    assert publish_response1.json()["message"] == "Results published successfully"

    # Run the second simulation
    simulation_response2 = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert simulation_response2.status_code == 200
    simulation_id2 = simulation_response2.json()["simulation_id"]

    # Try to publish the second simulation results
    publish_response2 = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id2},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert publish_response2.status_code == 200
    assert publish_response2.json()["status"] == "success"

    # Check if the first simulation results are still marked as published in the database
    simulation_result1 = db_session.exec(select(SimulationResult).where(SimulationResult.id == simulation_id1)).one()
    assert simulation_result1.published == False

    # Check if the second simulation results are not marked as published in the database
    simulation_result2 = db_session.exec(select(SimulationResult).where(SimulationResult.id == simulation_id2)).one()
    assert simulation_result2.published == True

def test_get_published_results_for_league(client: TestClient, db_session: Session):
    global ADMIN_TOKEN
    # Run a simulation
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert simulation_response.status_code == 200
    simulation_id = simulation_response.json()["simulation_id"]

    # Publish the simulation results
    publish_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "success"
    assert publish_response.json()["message"] == "Results published successfully"

    # Get the published results for the league
    get_published_response = client.post(
        "/get_published_results_for_league",
        json={"name": "comp_test"}
    )
    assert get_published_response.status_code == 200
    published_result = get_published_response.json()
    print(published_result)
    assert "id" in published_result
    # Check if the simulation results are marked as published in the database
    simulation_result = db_session.exec(select(SimulationResult).where(SimulationResult.id == simulation_id)).one()
    assert simulation_result.published == True