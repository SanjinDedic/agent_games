from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import League
from backend.games.simulation_task import aggregate_simulation_results, run_simulation


@pytest.fixture
def test_league(db_session: Session) -> League:
    """Create a test league for simulations"""
    # First check if league exists and delete if it does
    existing = db_session.exec(
        select(League).where(League.name == "test_league")
    ).first()
    if existing:
        db_session.delete(existing)
        db_session.commit()

    league = League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="prisoners_dilemma",
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    return league


def test_simulation_task_success(celery_workers, test_league: League):
    """Test successful simulation scenarios"""

    # Test case 1: Basic simulation request with minimal fields
    result = run_simulation.delay(
        league_id=test_league.id,
        game_name="prisoners_dilemma",
        num_simulations=100,
    ).get(timeout=60)
    assert result["status"] == "success"
    assert "simulation_results" in result

    # Test case 2: Simulation with custom rewards
    result = run_simulation.delay(
        league_id=test_league.id,
        game_name="prisoners_dilemma",
        num_simulations=100,
        custom_rewards=[4, 0, 6, 2],
    ).get(timeout=60)
    assert "simulation_results" in result

    # Test case 3: Simulation with player feedback
    result = run_simulation.delay(
        league_id=test_league.id,
        game_name="prisoners_dilemma",
        num_simulations=100,
        player_feedback=True,
    ).get(timeout=60)
    assert "feedback" in result
    assert "player_feedback" in result


def test_aggregate_simulation_results_success():
    """Test successful aggregation of simulation results"""
    simulation_results = [
        {
            "points": {"player1": 10, "player2": 20},
            "table": {"wins": {"player1": 1, "player2": 2}},
        },
        {
            "points": {"player1": 15, "player2": 25},
            "table": {"wins": {"player1": 2, "player2": 3}},
        },
    ]

    result = aggregate_simulation_results(simulation_results, 2)
    assert result["total_points"] == {"player1": 25, "player2": 45}
    assert result["num_simulations"] == 2
    assert "table" in result
