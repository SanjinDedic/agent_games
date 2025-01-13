from datetime import datetime, timedelta

import pytest
from database.db_models import League, SimulationResult
from fastapi.testclient import TestClient
from sqlmodel import Session, select


@pytest.fixture(scope="function")
def comp_test_league(db_session: Session) -> League:
    """Create comp_test league for testing simulations"""
    # Delete any existing league and its simulation results first
    existing_league = db_session.exec(
        select(League).where(League.name == "comp_test")
    ).first()
    if existing_league:
        # First delete associated simulation results
        simulation_results = db_session.exec(
            select(SimulationResult).where(
                SimulationResult.league_id == existing_league.id
            )
        ).all()
        for result in simulation_results:
            db_session.delete(result)
        db_session.delete(existing_league)
        db_session.commit()

    # Create new league
    league = League(
        name="comp_test",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        folder="leagues/admin/comp_test",
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()

    yield league

    # Clean up after test
    # Delete associated simulation results first
    simulation_results = db_session.exec(
        select(SimulationResult).where(SimulationResult.league_id == league.id)
    ).all()
    for result in simulation_results:
        db_session.delete(result)
    db_session.delete(league)
    db_session.commit()


def test_greedy_pig_simulation(
    client: TestClient, auth_headers: dict, comp_test_league: League
):
    simulation_response = client.post(
        "/admin/run-simulation",
        json={"league_name": "comp_test", "num_simulations": 100, "use_docker": False},
        headers=auth_headers,
    )
    assert simulation_response.status_code == 200
    response_data = simulation_response.json()
    assert "data" in response_data
    assert "total_points" in response_data["data"]


def test_greedy_pig_simulation_with_custom_rewards(
    client: TestClient, auth_headers: dict, comp_test_league: League
):
    custom_rewards = [15, 10, 5, 3, 2, 1]
    simulation_response = client.post(
        "/admin/run-simulation",
        json={
            "league_name": "comp_test",
            "num_simulations": 100,
            "custom_rewards": custom_rewards,
            "use_docker": False,
        },
        headers=auth_headers,
    )
    assert simulation_response.status_code == 200
    response_data = simulation_response.json()
    assert "data" in response_data
    assert "total_points" in response_data["data"]
    assert "rewards" in response_data["data"]
    assert response_data["data"]["rewards"] == custom_rewards
