from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    League,
    Submission,
    SubmissionMetadata,
    Team,
)
from backend.tasks.simulation_task import aggregate_simulation_results, run_simulation
from backend.time_utils import utc_now


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
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
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


# Direct (in-process) calls of the task function: the .delay() tests above run
# the body inside a worker container, so only these direct calls give the test
# process visibility into run_simulation's branches.

COLLUDER_CODE = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 'collude'
"""


class _StubGame:
    """Minimal game double for exercising run_simulation's error branches."""

    def __init__(self, league):
        self.players = [object()]
        self.scores = {}

    def add_player(self, code, name):
        self.players.append(object())

    def reset(self):
        pass

    def run_single_game_with_feedback(self, custom_rewards=None):
        return {"feedback": "stub feedback", "player_feedback": "stub pf"}

    def play_game(self, custom_rewards=None):
        return {"points": {"stub": 1}, "table": {}}

    def get_player_strategies(self):
        return {}


def _stub_factory(monkeypatch, game_class):
    monkeypatch.setattr(
        "backend.tasks.simulation_task.GameFactory",
        SimpleNamespace(get_game_class=lambda name: game_class),
    )


def test_run_simulation_direct_success(db_session, test_league):
    """No submissions in the league -> validation players play the games."""
    result = run_simulation(
        league_id=test_league.id,
        game_name="prisoners_dilemma",
        num_simulations=3,
    )
    assert result["status"] == "success"
    assert result["player_feedback"] == "No player feedback"
    sim = result["simulation_results"]
    assert sim["num_simulations"] == 3
    assert sim["total_points"]  # validation players scored
    assert "strategies" in sim


def test_run_simulation_direct_with_player_feedback(db_session, test_league):
    result = run_simulation(
        league_id=test_league.id,
        game_name="prisoners_dilemma",
        num_simulations=2,
        player_feedback=True,
    )
    assert result["status"] == "success"
    assert result["feedback"] != "No feedback"


def test_run_simulation_direct_with_submissions(db_session, test_league):
    """League submissions replace the validation players; a submission whose
    code cannot construct a player is skipped, not fatal."""
    now = utc_now()
    teams = {}
    for name, code in (("good_team", COLLUDER_CODE), ("broken_team", "not python !")):
        team = Team(name=name, school_name="Test School", league_id=test_league.id)
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)
        meta = SubmissionMetadata(team_id=team.id, league_id=test_league.id, timestamp=now)
        db_session.add(meta)
        db_session.commit()
        db_session.refresh(meta)
        db_session.add(Submission(code=code, timestamp=now, metadata_id=meta.id))
        db_session.commit()
        teams[name] = team

    result = run_simulation(
        league_id=test_league.id,
        game_name="prisoners_dilemma",
        num_simulations=2,
    )
    assert result["status"] == "success"
    points = result["simulation_results"]["total_points"]
    assert set(points) == {"good_team"}  # broken_team failed construction


def test_run_simulation_direct_submission_fetch_error(monkeypatch, db_session, test_league):
    """A DB error while fetching submissions keeps the validation players."""

    def boom(session, league_id):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(
        "backend.routes.user.user_db.get_latest_submissions_for_league", boom
    )
    result = run_simulation(
        league_id=test_league.id,
        game_name="prisoners_dilemma",
        num_simulations=2,
    )
    assert result["status"] == "success"
    assert result["simulation_results"]["total_points"]


def test_run_simulation_direct_no_players(monkeypatch, db_session):
    class NoPlayersGame(_StubGame):
        def __init__(self, league):
            super().__init__(league)
            self.players = []

    _stub_factory(monkeypatch, NoPlayersGame)
    result = run_simulation(league_id=999_999, game_name="prisoners_dilemma")
    assert result["status"] == "error"
    assert result["message"] == "No players loaded for simulation"
    assert result["simulation_results"]["total_points"] == {}


def test_run_simulation_direct_feedback_error(monkeypatch, db_session):
    class FeedbackErrorGame(_StubGame):
        def run_single_game_with_feedback(self, custom_rewards=None):
            raise RuntimeError("feedback exploded")

    _stub_factory(monkeypatch, FeedbackErrorGame)
    result = run_simulation(
        league_id=999_999,
        game_name="prisoners_dilemma",
        num_simulations=2,
        player_feedback=True,
    )
    assert result["status"] == "error"
    assert "Error running feedback game" in result["message"]


def test_run_simulation_direct_simulation_error(monkeypatch, db_session):
    class PlayErrorGame(_StubGame):
        def play_game(self, custom_rewards=None):
            raise RuntimeError("game exploded")

    _stub_factory(monkeypatch, PlayErrorGame)
    result = run_simulation(
        league_id=999_999,
        game_name="prisoners_dilemma",
        num_simulations=2,
    )
    assert result["status"] == "error"
    assert "Error running simulations" in result["message"]


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
