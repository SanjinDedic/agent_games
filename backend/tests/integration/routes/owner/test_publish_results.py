import json
from datetime import timedelta

import pytest
from sqlmodel import Session, select


from backend.database.db_models import League, SimulationResult
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def publish_setup(db_session: Session) -> tuple:
    """Setup, league, and simulation results for testing publishing"""
    db_session.commit()
    
    # Create a league
    league = League(
        name="publish_test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    
    # Create two simulation results
    sim_result1 = SimulationResult(
        league_id=league.id,
        timestamp=utc_now(),
        num_simulations=10,
        custom_rewards="[10, 8, 6, 4, 3, 2, 1]",
        published=False,
    )
    sim_result2 = SimulationResult(
        league_id=league.id,
        timestamp=utc_now() + timedelta(hours=1),
        num_simulations=20,
        custom_rewards="[10, 8, 6, 4, 3, 2, 1]",
        published=False,
    )
    db_session.add(sim_result1)
    db_session.add(sim_result2)
    db_session.commit()
    db_session.refresh(sim_result1)
    db_session.refresh(sim_result2)
    
    # Create token
    token = create_access_token(
        data={
            "sub": "test_owner",
            "role": "owner",
        },
        expires_delta=timedelta(minutes=30),
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    return league, [sim_result1, sim_result2], token, headers


def test_publish_results_success(client, publish_setup, db_session):
    """Test successful publishing of simulation results"""
    league, sim_results, _, headers = publish_setup

    # Test case 1: Publish with string feedback
    response = client.post(
        "/owner/publish-results",
        headers=headers,
        json={
            "league_id": league.id,
            "id": sim_results[0].id,
            "feedback": "Test string feedback",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "published successfully" in data["message"]

    # Verify result was published and has string feedback
    db_session.refresh(sim_results[0])
    assert sim_results[0].published is True
    assert sim_results[0].feedback_str == "Test string feedback"
    assert sim_results[0].feedback_json is None

    # Test case 2: Publish with JSON feedback
    json_feedback = {
        "analysis": {
            "top_performer": "Team1",
            "notes": "Great cooperation strategy"
        }
    }
    response = client.post(
        "/owner/publish-results",
        headers=headers,
        json={
            "league_id": league.id,
            "id": sim_results[1].id,
            "feedback": json_feedback,
        },
    )
    assert response.status_code == 200

    # Verify result was published and has JSON feedback
    db_session.refresh(sim_results[0])
    db_session.refresh(sim_results[1])
    assert sim_results[1].published is True
    assert sim_results[1].feedback_json is not None
    loaded_feedback = json.loads(sim_results[1].feedback_json)
    assert loaded_feedback["analysis"]["top_performer"] == "Team1"

    # Test case 3: Publish without feedback
    response = client.post(
        "/owner/publish-results",
        headers=headers,
        json={
            "league_id": league.id,
            "id": sim_results[0].id,
        },
    )
    assert response.status_code == 200


def test_publish_results_failures(client, publish_setup, db_session):
    """Test failure cases for publishing results"""
    league, sim_results, _, headers = publish_setup
    
    # Test case 1: Non-existent league
    response = client.post(
        "/owner/publish-results",
        headers=headers,
        json={
            "league_id": 99999,
            "id": sim_results[0].id,
        },
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    
    # Test case 2: Non-existent simulation result
    response = client.post(
        "/owner/publish-results",
        headers=headers,
        json={
            "league_id": league.id,
            "id": 99999,
        },
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    
