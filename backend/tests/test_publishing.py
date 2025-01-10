# tests/test_publishing.py

import json

import pytest
from api import app
from database import get_db_engine
from database.db_models import SimulationResult
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from tests.database_setup import setup_test_db


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


def test_publish_results_with_markdown_feedback(client, db_session, admin_token):
    # First, run a simulation
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response.status_code == 200
    simulation_id = simulation_response.json()["data"]["id"]

    # Publish with markdown feedback
    markdown_feedback = """# Simulation Results
    
    ## Performance Analysis
    - Good performance from Team A
    - Team B needs improvement
    """

    publish_response = client.post(
        "/publish_results",
        json={
            "league_name": "comp_test",
            "id": simulation_id,
            "feedback": markdown_feedback,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "success"

    # Verify the published results contain the feedback
    get_results_response = client.post(
        "/get_published_results_for_league", json={"name": "comp_test"}
    )
    assert get_results_response.status_code == 200
    results = get_results_response.json()["data"]
    assert results["feedback"] == markdown_feedback


def test_publish_results_with_json_feedback(client, db_session, admin_token):
    # First, run a simulation
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response.status_code == 200
    simulation_id = simulation_response.json()["data"]["id"]

    # Publish with JSON feedback
    json_feedback = {
        "analysis": {
            "top_performer": "Team A",
            "metrics": {"average_score": 85.5, "win_rate": 0.75},
            "recommendations": [
                "Team B should be more aggressive",
                "Team C needs better defense",
            ],
        }
    }

    publish_response = client.post(
        "/publish_results",
        json={
            "league_name": "comp_test",
            "id": simulation_id,
            "feedback": json_feedback,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "success"

    # Verify the published results contain the feedback
    get_results_response = client.post(
        "/get_published_results_for_league", json={"name": "comp_test"}
    )
    assert get_results_response.status_code == 200
    results = get_results_response.json()["data"]
    assert results["feedback"] == json_feedback


def test_publish_results_feedback_overwrite(client, db_session, admin_token):
    """Test that publishing new results overwrites old feedback"""
    # First simulation with markdown feedback
    simulation_response1 = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response1.status_code == 200
    simulation_id1 = simulation_response1.json()["data"]["id"]

    markdown_feedback = "# First Feedback"
    publish_response1 = client.post(
        "/publish_results",
        json={
            "league_name": "comp_test",
            "id": simulation_id1,
            "feedback": markdown_feedback,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response1.status_code == 200

    # Second simulation with JSON feedback
    simulation_response2 = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response2.status_code == 200
    simulation_id2 = simulation_response2.json()["data"]["id"]

    json_feedback = {"message": "Second Feedback"}
    publish_response2 = client.post(
        "/publish_results",
        json={
            "league_name": "comp_test",
            "id": simulation_id2,
            "feedback": json_feedback,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response2.status_code == 200

    # Verify only the latest feedback is present
    get_results_response = client.post(
        "/get_published_results_for_league", json={"name": "comp_test"}
    )
    assert get_results_response.status_code == 200
    results = get_results_response.json()["data"]
    assert results["feedback"] == json_feedback

    # Verify first simulation is no longer published
    simulation1 = db_session.exec(
        select(SimulationResult).where(SimulationResult.id == simulation_id1)
    ).one()
    assert simulation1.published is False
    assert simulation1.feedback_str == markdown_feedback
    assert simulation1.feedback_json is None

    # Verify second simulation is published
    simulation2 = db_session.exec(
        select(SimulationResult).where(SimulationResult.id == simulation_id2)
    ).one()
    assert simulation2.published is True
    assert simulation2.feedback_str is None
    assert simulation2.feedback_json == json.dumps(json_feedback)


def test_publish_results_no_feedback(client, db_session, admin_token):
    """Test publishing results without any feedback"""
    # Add use_docker=False to prevent automatic feedback generation
    simulation_response = client.post(
        "/run_simulation",
        json={"league_name": "comp_test", "num_simulations": 10, "use_docker": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert simulation_response.status_code == 200
    simulation_id = simulation_response.json()["data"]["id"]

    # Publish without feedback
    publish_response = client.post(
        "/publish_results",
        json={"league_name": "comp_test", "id": simulation_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "success"

    # Verify the published results have no feedback
    get_results_response = client.post(
        "/get_published_results_for_league", json={"name": "comp_test"}
    )
    assert get_results_response.status_code == 200
    results = get_results_response.json()["data"]
    assert results["feedback"] is None

    # Verify database state
    simulation = db_session.exec(
        select(SimulationResult).where(SimulationResult.id == simulation_id)
    ).one()
    assert simulation.published is True
    assert simulation.feedback_str is None
    assert simulation.feedback_json is None


def test_publish_nonexistent_simulation(client, admin_token, db_session):
    """Tests publishing results for a non-existent simulation.
    This covers lines 373-375 in api.py where simulation existence is verified."""

    response = client.post(
        "/publish_results",
        json={
            "league_name": "comp_test",
            "id": 99999,  # Non-existent simulation ID
            "feedback": "Test feedback",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "not found" in response.json()["message"]
