from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (Institution, League, SimulationResult,
                                        Team)
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def league_results_setup(db_session: Session) -> tuple:
    """Setup institution, league, and simulation results for testing"""
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
    
    # Create a league with simulation results
    league = League(
        name="results_test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    
    # Create simulation results
    sim_result1 = SimulationResult(
        league_id=league.id,
        timestamp=datetime.now(),
        num_simulations=10,
        custom_rewards="[10, 8, 6, 4, 3, 2, 1]",
        published=True,
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


def test_get_all_league_results_success(client, league_results_setup, db_session):
    """Test successful retrieval of league results"""
    institution, league, simulation_results, _, headers = league_results_setup
    
    # Get results for league with simulations
    response = client.post(
        "/institution/get-all-league-results",
        headers=headers,
        json={"name": league.name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data["data"]
    
    # Verify all results are included
    results = data["data"]["results"]
    assert len(results) == len(simulation_results)
    
    # Check result data structure
    for result in results:
        assert "id" in result
        assert "league_name" in result
        assert "timestamp" in result
        assert "total_points" in result
        assert "table" in result
        assert "num_simulations" in result
        assert "rewards" in result
    
    # Create an empty league
    empty_league = League(
        name="empty_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(empty_league)
    db_session.commit()
    
    # Get results for empty league
    response = client.post(
        "/institution/get-all-league-results",
        headers=headers,
        json={"name": empty_league.name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data["data"]
    assert len(data["data"]["results"]) == 0


def test_get_all_league_results_failures(client, league_results_setup, db_session):
    """Test failure cases for getting league results"""
    institution, league, simulation_results, _, headers = league_results_setup
    
    # Test case 1: Non-existent league
    response = client.post(
        "/institution/get-all-league-results",
        headers=headers,
        json={"name": "non_existent_league"},
    )
    assert response.status_code == 200  # API returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    
    # Test case 2: League from different institution
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
    
    # Try to get results for other institution's league
    response = client.post(
        "/institution/get-all-league-results",
        headers=headers,
        json={"name": other_league.name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    
    # Test case 3: Empty league name
    response = client.post(
        "/institution/get-all-league-results",
        headers=headers,
        json={"name": ""},
    )
    assert response.status_code == 422
    
    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/institution/get-all-league-results",
        json={"name": league.name},
    )
    assert response.status_code == 401
    
    # Test case 5: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/institution/get-all-league-results",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={"name": league.name},
    )
    assert response.status_code == 403