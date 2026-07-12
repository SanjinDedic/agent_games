from datetime import timedelta

import pytest
from sqlmodel import Session

from backend.database.db_models import League, Team
from backend.tasks.simulation_task import run_simulation
from backend.tasks.validation_task import (
    run_validation,
    timeout_validation_result,
)
from backend.time_utils import utc_now


@pytest.fixture
def test_league(db_session: Session) -> League:
    """Create a test league for Celery task tests"""
    league = League(
        name="celery_test_league",
        game="prisoners_dilemma",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    return league


@pytest.fixture
def test_team(db_session: Session, test_league: League) -> Team:
    """Create a test team for Celery task tests"""
    team = Team(
        name="celery_test_team",
        school_name="Celery Test School",
        password_hash="test_hash",
        league_id=test_league.id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def test_validation_workflow(celery_workers, test_team: Team):
    """Valid code runs through the validation task on a real worker."""
    valid_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
"""
    result = run_validation.delay(
        code=valid_code,
        game_name="prisoners_dilemma",
        team_name=test_team.name,
    ).get(timeout=20)
    assert result["status"] == "success"
    assert "simulation_results" in result
    # Validation runs against the built-in bots, whose strategies ship with
    # the results (the submitted team has none).
    strategies = result["simulation_results"]["strategies"]
    assert strategies["TitForTat"]
    assert test_team.name not in strategies


def test_simulation_workflow(celery_workers, test_league: League):
    """Basic and custom-rewards simulations through the task."""
    result = run_simulation.delay(
        league_id=test_league.id,
        game_name="prisoners_dilemma",
        num_simulations=10,
    ).get(timeout=60)
    assert result["status"] == "success"
    assert "simulation_results" in result
    # No submissions in this league, so the validation players (and their
    # strategies) are in play.
    assert result["simulation_results"]["strategies"]["AlwaysDefect"]

    result = run_simulation.delay(
        league_id=test_league.id,
        game_name="prisoners_dilemma",
        num_simulations=10,
        custom_rewards=[10, 5, 3, 0],
    ).get(timeout=60)
    assert result["status"] == "success"


def test_validation_timeout(celery_workers):
    """An agent stuck in a loop is stopped by the soft time limit.

    SoftTimeLimitExceeded fires inside make_decision; the game engine
    re-raises it as ValueError (abort-on-error, no default action) and the
    task boundary spots the soft limit in the exception chain, reporting the
    canonical timeout message instead of an agent bug. An agent that swallows
    the soft limit itself still spins until the hard SIGKILL — that path is
    covered by test_worker_resilience.py.
    """
    timeout_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        while True:
            pass
"""
    result = run_validation.delay(
        code=timeout_code,
        game_name="prisoners_dilemma",
        team_name="timeout_team",
    ).get(timeout=15)
    assert result["status"] == "error"
    assert result["message"].startswith("Your agent consumes too much time")


def test_validation_timeout_result_shape():
    """The hard-kill fallback dict carries the exact prefix-matched message."""
    result = timeout_validation_result()
    assert result["status"] == "error"
    assert result["message"].startswith("Your agent consumes too much time")
    assert set(result) == {
        "status",
        "message",
        "feedback",
        "simulation_results",
        "duration_ms",
        "traceback",
        "stdout",
    }


def test_task_isolation(celery_workers):
    """A fresh process per task (worker_max_tasks_per_child=1) means one
    agent's monkeypatching of games.* cannot leak into a later validation."""
    contaminating_code = """
from games.prisoners_dilemma.player import Player

Player.contaminated = True

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
"""
    probe_code = """
from games.prisoners_dilemma.player import Player

print("CONTAMINATED" if getattr(Player, "contaminated", False) else "CLEAN")

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
"""
    result = run_validation.delay(
        code=contaminating_code,
        game_name="prisoners_dilemma",
        team_name="dirty_team",
    ).get(timeout=20)
    assert result["status"] == "success"

    result = run_validation.delay(
        code=probe_code,
        game_name="prisoners_dilemma",
        team_name="clean_team",
    ).get(timeout=20)
    assert result["status"] == "success"
    assert "CLEAN" in (result.get("stdout") or "")
    assert "CONTAMINATED" not in (result.get("stdout") or "")


def test_concurrent_simulations(celery_workers, test_league: League):
    """Multiple queued simulations all complete."""
    async_results = [
        run_simulation.delay(
            league_id=test_league.id,
            game_name="prisoners_dilemma",
            num_simulations=10,
        )
        for _ in range(5)
    ]
    for async_result in async_results:
        result = async_result.get(timeout=120)
        assert result["status"] == "success"
