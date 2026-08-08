from datetime import timedelta

import pytest
from sqlmodel import Session, select


from backend.database.db_models import League, SimulationResult, Team
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def league_results_setup(db_session: Session) -> tuple:
    """Setup, league, and simulation results for testing"""
    db_session.commit()
    
    # Create a league with simulation results
    league = League(
        name="results_test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    
    # Create simulation results
    sim_result1 = SimulationResult(
        league_id=league.id,
        timestamp=utc_now(),
        num_simulations=10,
        custom_rewards="[10, 8, 6, 4, 3, 2, 1]",
        published=True,
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
    
    # Create token
    token = create_access_token(
        data={
            "sub": "test_admin",
            "role": "admin",
        },
        expires_delta=timedelta(minutes=30),
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    return league, [sim_result1, sim_result2], token, headers


def test_get_all_league_results_success(client, league_results_setup, db_session):
    """Test successful retrieval of league results"""
    league, simulation_results, _, headers = league_results_setup
    
    # Get results for league with simulations
    response = client.post(
        "/admin/get-all-league-results",
        headers=headers,
        json={"league_id": league.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data

    # Verify all results are included
    results = data["results"]
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
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(empty_league)
    db_session.commit()
    
    # Get results for empty league
    response = client.post(
        "/admin/get-all-league-results",
        headers=headers,
        json={"league_id": empty_league.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 0


def test_get_all_league_results_failures(client, league_results_setup, db_session):
    """Test failure cases for getting league results"""
    league, simulation_results, _, headers = league_results_setup
    
    # Test case 1: Non-existent league
    response = client.post(
        "/admin/get-all-league-results",
        headers=headers,
        json={"league_id": 99999},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    