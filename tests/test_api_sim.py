import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from models_db import League, SimulationResult
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

def test_run_simulation(client, db_session, admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 100},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200
    assert "total_points" in simulation_response.json()["data"]

    simulation_results = db_session.exec(select(SimulationResult)).all()
    assert len(simulation_results) > 0

def test_get_all_league_results(client, admin_token, non_admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200
    
    league_results_response = client.post(
        "/get_all_league_results",
        json={"name": "comp_test"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert league_results_response.status_code == 200
    assert isinstance(league_results_response.json()["data"]["all_results"], list)

    unauthorized_response = client.post(
        "/get_all_league_results",
        json={"name": "comp_test"},
        headers={"Authorization": f"Bearer {non_admin_token}"}
    )
    assert unauthorized_response.json()["message"] == "Only admin users can view league results"

def test_publish_results(client, db_session, admin_token, non_admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200
    simulation_id = simulation_response.json()["data"]["simulation_id"]

    publish_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "success"
    assert publish_response.json()["message"] == "Simulation results for league 'comp_test' published successfully"

    simulation_result = db_session.exec(select(SimulationResult).where(SimulationResult.id == simulation_id)).one()
    assert simulation_result.published == True

    publish_again_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert publish_again_response.status_code == 200
    assert publish_again_response.json()["status"] == "success"
    assert publish_again_response.json()["message"] == "Simulation results for league 'comp_test' published successfully"

    simulation_result = db_session.exec(select(SimulationResult).where(SimulationResult.id == simulation_id)).one()
    assert simulation_result.published == True

    unauthorized_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {non_admin_token}"}
    )
    assert unauthorized_response.json()["message"] == "Only admin users can publish league results"

    simulation_result = db_session.exec(select(SimulationResult).where(SimulationResult.id == simulation_id)).one()
    assert simulation_result.published == True

def test_publish_one_simulation_per_league(client, db_session, admin_token):
    simulation_response1 = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response1.status_code == 200
    simulation_id1 = simulation_response1.json()["data"]["simulation_id"]

    publish_response1 = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id1},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert publish_response1.status_code == 200
    assert publish_response1.json()["status"] == "success"
    assert publish_response1.json()["message"] == "Simulation results for league 'comp_test' published successfully"

    simulation_response2 = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response2.status_code == 200
    simulation_id2 = simulation_response2.json()["data"]["simulation_id"]

    publish_response2 = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id2},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert publish_response2.status_code == 200
    assert publish_response2.json()["status"] == "success"

    simulation_result1 = db_session.exec(select(SimulationResult).where(SimulationResult.id == simulation_id1)).one()
    assert simulation_result1.published == False

    simulation_result2 = db_session.exec(select(SimulationResult).where(SimulationResult.id == simulation_id2)).one()
    assert simulation_result2.published == True

def test_get_published_results_for_league(client, db_session, admin_token):
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert simulation_response.status_code == 200
    simulation_id = simulation_response.json()["data"]["simulation_id"]

    publish_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "success"
    assert publish_response.json()["message"] == "Simulation results for league 'comp_test' published successfully"

    get_published_response = client.post(
        "/get_published_results_for_league",
        json={"name": "comp_test"}
    )
    assert get_published_response.status_code == 200
    published_result = get_published_response.json()["data"]

    simulation_result = db_session.exec(select(SimulationResult).where(SimulationResult.id == simulation_id)).one()
    assert simulation_result.published == True


'''
def test_get_published_results_for_all_leagues(client, db_session, admin_token):
    # Test getting published results for all leagues
    response = client.post("/get_published_results_for_all_leagues")
    print(response.json())
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert len(response.json()["data"]) == 1
    '''