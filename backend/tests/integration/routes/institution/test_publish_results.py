import json
from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, League, SimulationResult
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def publish_setup(db_session: Session) -> tuple:
    """Setup institution, league, and simulation results for testing publishing"""
    # Create an institution
    institution = Institution(
        name="test_institution",
        contact_person="Test Person",
        contact_email="test@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="test_hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)
    
    # Create a league
    league = League(
        name="publish_test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    
    # Create two simulation results
    sim_result1 = SimulationResult(
        league_id=league.id,
        timestamp=datetime.now(),
        num_simulations=10,
        custom_rewards="[10, 8, 6, 4, 3, 2, 1]",
        published=False,
    )
    sim_result2 = SimulationResult(
        league_id=league.id,
        timestamp=datetime.now() + timedelta(hours=1),
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
            "sub": institution.name,
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(minutes=30),
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    return institution, league, [sim_result1, sim_result2], token, headers


def test_publish_results_success(client, publish_setup, db_session):
    """Test successful publishing of simulation results"""
    institution, league, sim_results, _, headers = publish_setup

    # Test case 1: Publish with string feedback
    response = client.post(
        "/institution/publish-results",
        headers=headers,
        json={
            "league_name": league.name,
            "id": sim_results[0].id,
            "feedback": "Test string feedback",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
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
        "/institution/publish-results",
        headers=headers,
        json={
            "league_name": league.name,
            "id": sim_results[1].id,
            "feedback": json_feedback,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify result was published and has JSON feedback
    db_session.refresh(sim_results[0])
    db_session.refresh(sim_results[1])
    assert sim_results[1].published is True
    assert sim_results[1].feedback_json is not None
    loaded_feedback = json.loads(sim_results[1].feedback_json)
    assert loaded_feedback["analysis"]["top_performer"] == "Team1"

    # Test case 3: Publish without feedback
    response = client.post(
        "/institution/publish-results",
        headers=headers,
        json={
            "league_name": league.name,
            "id": sim_results[0].id,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_publish_results_failures(client, publish_setup, db_session):
    """Test failure cases for publishing results"""
    institution, league, sim_results, _, headers = publish_setup
    
    # Test case 1: Non-existent league
    response = client.post(
        "/institution/publish-results",
        headers=headers,
        json={
            "league_name": "non_existent_league",
            "id": sim_results[0].id,
        },
    )
    assert response.status_code == 200  # API returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    
    # Test case 2: Non-existent simulation result
    response = client.post(
        "/institution/publish-results",
        headers=headers,
        json={
            "league_name": league.name,
            "id": 99999,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    
    # Test case 3: League from different institution
    # Create another institution and league
    other_institution = Institution(
        name="other_institution",
        contact_person="Other Person",
        contact_email="other@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="test_hash",
    )
    db_session.add(other_institution)
    db_session.commit()
    
    other_league = League(
        name="other_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=other_institution.id,
    )
    db_session.add(other_league)
    db_session.commit()
    
    # Create result for the other league
    other_result = SimulationResult(
        league_id=other_league.id,
        timestamp=datetime.now(),
        num_simulations=10,
        custom_rewards="[10, 8, 6, 4, 3, 2, 1]",
        published=False,
    )
    db_session.add(other_result)
    db_session.commit()
    
    # Try to publish result from another institution
    response = client.post(
        "/institution/publish-results",
        headers=headers,
        json={
            "league_name": other_league.name,
            "id": other_result.id,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    
    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/institution/publish-results",
        json={
            "league_name": league.name,
            "id": sim_results[0].id,
        },
    )
    assert response.status_code == 401
    
    # Test case 5: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/institution/publish-results",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={
            "league_name": league.name,
            "id": sim_results[0].id,
        },
    )
    assert response.status_code == 403
