import json
from datetime import datetime, timedelta

import pytest
from sqlmodel import select

from backend.config import ROOT_DIR
from backend.database.db_models import League, SimulationResult
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def user_token(db_session):
    """Create a regular user token"""
    return create_access_token(
        data={"sub": "test_user", "role": "user"}, expires_delta=timedelta(minutes=30)
    )


@pytest.fixture
def non_admin_token(db_session):
    """Create a non-admin token"""
    return create_access_token(
        data={"sub": "test_non_admin", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )


@pytest.fixture
def setup_comp_test_league(db_session):
    """Setup comp_test league for testing"""
    # First check if league exists
    league = db_session.exec(select(League).where(League.name == "comp_test")).first()
    if league:
        return league

    league = League(
        name="comp_test",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        active=True,
    )
    db_session.add(league)
    db_session.commit()

    return league


def test_league_creation(client, auth_headers):
    """Test league creation with various scenarios"""
    # Test successful creation
    response = client.post(
        "/admin/league-create",
        json={"name": "week1", "game": "greedy_pig"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Test unauthorized access
    response = client.post("/admin/league-create")
    assert response.status_code == 401

    # Test invalid game name
    response = client.post(
        "/admin/league-create",
        json={"name": "test_league", "game": "invalid_game"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    data = response.json()
    assert "Game must be one of" in str(data["detail"])

    # Test duplicate league name
    response = client.post(
        "/admin/league-create",
        json={"name": "week1", "game": "greedy_pig"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "already exists" in response.json()["message"]


def test_get_all_leagues(client, team_token, setup_comp_test_league):
    """Test retrieving all leagues"""
    response = client.get(
        "/user/get-all-leagues", headers={"Authorization": f"Bearer {team_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    leagues = data["data"]["leagues"]

    # Verify required leagues exist
    league_names = [league["name"] for league in leagues]
    assert "unassigned" in league_names
    assert "comp_test" in league_names

    # Verify league properties
    for league in leagues:
        assert "id" in league
        assert "game" in league
        assert "created_date" in league
        assert "expiry_date" in league


def test_league_simulation_workflow(
    client, auth_headers, setup_comp_test_league, db_session
):
    # First simulation request
    simulation_response = client.post(
        "/admin/run-simulation",
        json={
            "league_id": setup_comp_test_league.id,
            "num_simulations": 10,
            "use_docker": False,
        },
        headers=auth_headers,
    )
    assert simulation_response.status_code == 200
    sim_data = simulation_response.json()
    assert sim_data["status"] == "success"
    assert "data" in sim_data
    simulation_id = sim_data["data"]["id"]

    markdown_feedback = """# Simulation Results
    ## Performance Analysis
    - Good performance from Team A
    - Team B needs improvement"""

    publish_response = client.post(
        "/admin/publish-results",
        json={
            "league_name": "comp_test",
            "id": simulation_id,
            "feedback": markdown_feedback,
        },
        headers=auth_headers,
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "success"

    # Verify published results with markdown feedback
    results_response = client.post(
        "/user/get-published-results-for-league", json={"name": "comp_test"}
    )
    assert results_response.status_code == 200
    results = results_response.json()["data"]
    assert results is not None
    assert results["league_name"] == "comp_test"
    assert results["feedback"] == markdown_feedback

    # Test with JSON feedback - now using league_id
    simulation_response2 = client.post(
        "/admin/run-simulation",
        json={
            "league_id": setup_comp_test_league.id,  # Using league_id instead of league_name
            "num_simulations": 10,
            "use_docker": False,
        },
        headers=auth_headers,
    )
    assert simulation_response2.status_code == 200
    simulation_id2 = simulation_response2.json()["data"]["id"]

    json_feedback = {
        "analysis": {
            "top_performer": "Team A",
            "metrics": {"average_score": 85.5, "win_rate": 0.75},
            "recommendations": ["Team B should be more aggressive"],
        }
    }

    publish_response2 = client.post(
        "/admin/publish-results",
        json={
            "league_name": "comp_test",
            "id": simulation_id2,
            "feedback": json_feedback,
        },
        headers=auth_headers,
    )
    assert publish_response2.status_code == 200

    # Verify results and check feedback overwriting
    results_response = client.post(
        "/user/get-published-results-for-league", json={"name": "comp_test"}
    )
    assert results_response.status_code == 200
    results = results_response.json()["data"]
    assert results["feedback"] == json_feedback

    # Verify first simulation is no longer published
    simulation1 = db_session.exec(
        select(SimulationResult).where(SimulationResult.id == simulation_id)
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


def test_expiry_date_management(client, auth_headers, setup_comp_test_league):
    """Test league expiry date management"""
    new_expiry_date = datetime.now() + timedelta(days=30)

    # Test updating expiry date as admin
    response = client.post(
        "/admin/update-expiry-date",
        json={"date": new_expiry_date.isoformat(), "league": "comp_test"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "updated successfully" in response.json()["message"]

    # Test unauthorized access
    response = client.post(
        "/admin/update-expiry-date",
        json={"date": new_expiry_date.isoformat(), "league": "comp_test"},
    )
    assert response.status_code == 401


def test_publish_results_authorization(
    client, auth_headers, non_admin_token, setup_comp_test_league, db_session
):
    """Test results publishing authorization"""
    # Create a simulation result
    simulation = SimulationResult(
        league_id=setup_comp_test_league.id,
        timestamp=datetime.now(),
        num_simulations=10,
    )
    db_session.add(simulation)
    db_session.commit()

    # Test publishing as admin
    admin_response = client.post(
        "/admin/publish-results",
        json={"league_name": "comp_test", "id": simulation.id},
        headers=auth_headers,
    )
    assert admin_response.status_code == 200
    assert admin_response.json()["status"] == "success"

    # Test publishing as non-admin
    non_admin_response = client.post(
        "/admin/publish-results",
        json={"league_name": "comp_test", "id": simulation.id},
        headers={"Authorization": f"Bearer {non_admin_token}"},
    )
    assert non_admin_response.status_code == 403


def test_published_results_management(
    client, auth_headers, setup_comp_test_league, db_session
):
    """Test management of published results"""
    # First ensure no results are published
    leagues = db_session.exec(select(League)).all()
    for league in leagues:
        for sim in league.simulation_results:
            sim.published = False
    db_session.commit()

    # Verify empty results
    response = client.get(
        "/user/get-published-results-for-all-leagues", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]["all_results"]) == 0

    # Create and publish a result
    simulation = SimulationResult(
        league_id=setup_comp_test_league.id,
        timestamp=datetime.now(),
        num_simulations=10,
        published=True,
    )
    db_session.add(simulation)
    db_session.commit()

    # Verify published result is available
    response = client.get(
        "/user/get-published-results-for-all-leagues", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]["all_results"]) > 0
