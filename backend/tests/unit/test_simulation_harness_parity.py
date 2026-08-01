"""Parity contract for the in-browser simulation harness.

frontend/src/pyodide/simulation_harness.py replicates the deleted Celery
simulation task (player loading, one verbose feedback game, incremental
aggregation, envelope shapes). These tests exec the exact file the browser
ships under CPython — where the real backend.games package is importable, so
no filesystem shim is needed — and pin its behavior to the old task's
contract. greedy_pig reseeds `random` on every roll, so parity is structural
and statistical, never exact-value.

The harness file reaches the test container through the same read-only
volume as the exercise harness (docker-compose.yml).
"""

import importlib.util
import json
from pathlib import Path

import pytest

HARNESS_PATH = (
    Path(__file__).resolve().parents[3]
    / "frontend"
    / "src"
    / "pyodide"
    / "simulation_harness.py"
)

VALID_AGENT = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if self.unbanked_money >= 15:
            return "bank"
        return "continue"
"""

VALID_AGENT_2 = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if self.unbanked_money >= 21:
            return "bank"
        return "continue"
"""

BROKEN_AGENT = """
this is not python at all (
"""

# Loads fine but every decision is invalid, so the feedback game blows up.
INVALID_DECISION_AGENT = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "explode"
"""

SUCCESS_ENVELOPE_KEYS = {
    "status",
    "feedback",
    "player_feedback",
    "simulation_results",
    "skipped",
}
# The old task's simulation_results shape, exactly.
SIMULATION_RESULTS_KEYS = {
    "total_points",
    "num_simulations",
    "table",
    "requested_simulations",
    "capped",
    "strategies",
}
ERROR_ENVELOPE_KEYS = {"status", "message", "simulation_results"}


def _load_harness():
    """Fresh module per test: the harness keeps run state at module level."""
    spec = importlib.util.spec_from_file_location(
        "simulation_harness", HARNESS_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def harness():
    return _load_harness()


def _setup(harness, submissions, requested, custom_rewards=None):
    return json.loads(
        harness.setup_run_json(
            "greedy_pig",
            json.dumps(submissions) if submissions is not None else "",
            json.dumps(custom_rewards) if custom_rewards else "",
            requested,
        )
    )


def test_full_run_matches_old_task_contract(harness):
    submissions = {"team_alpha": VALID_AGENT, "team_beta": VALID_AGENT_2}
    setup = _setup(harness, submissions, requested=20)
    assert setup["status"] == "ok"
    assert sorted(setup["players"]) == ["team_alpha", "team_beta"]
    assert setup["skipped"] == []

    chunk = json.loads(harness.run_chunk_json(7))
    assert chunk == {"status": "ok", "completed": 7}
    chunk = json.loads(harness.run_chunk_json(13))
    assert chunk == {"status": "ok", "completed": 20}

    envelope = json.loads(harness.finalize_json(False))
    assert set(envelope) == SUCCESS_ENVELOPE_KEYS
    assert envelope["status"] == "success"

    results = envelope["simulation_results"]
    assert set(results) == SIMULATION_RESULTS_KEYS
    assert results["num_simulations"] == 20
    assert results["requested_simulations"] == 20
    assert results["capped"] is False
    # greedy_pig's play_game returns no "table"; the old aggregate emitted {}.
    assert results["table"] == {}
    # Real submissions declare no strategy — empty map, like the old task.
    assert results["strategies"] == {}

    # Default placement rewards hand out 10 points per game (ties split the
    # pool), so the total is invariant even though each game is random.
    assert set(results["total_points"]) == {"team_alpha", "team_beta"}
    assert sum(results["total_points"].values()) == pytest.approx(10 * 20)

    # The one verbose game produced the feedback contract that
    # GreedyPigFeedback.jsx consumes.
    feedback = envelope["feedback"]
    assert feedback["game"] == "greedy_pig"
    assert feedback["rounds"], "feedback game recorded no rounds"
    assert "final_results" in feedback
    assert "score_aggregate" in feedback
    first_roll = feedback["rounds"][0]["rolls"][0]
    assert {"roll_no", "dice_value", "busted", "players"} <= set(first_roll)


def test_cancelled_run_finalizes_partial_results(harness):
    submissions = {"team_alpha": VALID_AGENT, "team_beta": VALID_AGENT_2}
    assert _setup(harness, submissions, requested=50)["status"] == "ok"

    assert json.loads(harness.run_chunk_json(10))["completed"] == 10

    envelope = json.loads(harness.finalize_json(True))
    results = envelope["simulation_results"]
    assert results["capped"] is True
    assert results["num_simulations"] == 10
    assert results["requested_simulations"] == 50
    assert sum(results["total_points"].values()) == pytest.approx(10 * 10)


def test_broken_submission_is_skipped_not_fatal(harness):
    submissions = {"team_alpha": VALID_AGENT, "team_broken": BROKEN_AGENT}
    setup = _setup(harness, submissions, requested=5)
    assert setup["status"] == "ok"
    assert setup["players"] == ["team_alpha"]
    assert len(setup["skipped"]) == 1
    assert setup["skipped"][0]["team"] == "team_broken"
    assert setup["skipped"][0]["error"]

    json.loads(harness.run_chunk_json(5))
    envelope = json.loads(harness.finalize_json(False))
    assert envelope["skipped"][0]["team"] == "team_broken"
    assert set(envelope["simulation_results"]["total_points"]) == {"team_alpha"}


def test_no_loadable_players_error_envelope(harness):
    setup = _setup(harness, {"team_broken": BROKEN_AGENT}, requested=10)
    assert set(setup) == ERROR_ENVELOPE_KEYS
    assert setup["status"] == "error"
    # Exact old-task message: the frontend surfaces it verbatim.
    assert setup["message"] == "No players loaded for simulation"
    assert setup["simulation_results"] == {
        "total_points": {},
        "num_simulations": 10,
        "table": {},
    }


def test_feedback_game_failure_error_envelope(harness):
    setup = _setup(
        harness, {"team_bad": INVALID_DECISION_AGENT}, requested=10
    )
    assert setup["status"] == "error"
    assert setup["message"].startswith("Error running feedback game:")
    assert setup["simulation_results"]["num_simulations"] == 10


def test_empty_submissions_keep_validation_players(harness):
    setup = _setup(harness, None, requested=5)
    assert setup["status"] == "ok"
    # greedy_pig ships 7 validation bots, each declaring a strategy.
    assert len(setup["players"]) == 7

    json.loads(harness.run_chunk_json(5))
    envelope = json.loads(harness.finalize_json(False))
    strategies = envelope["simulation_results"]["strategies"]
    assert set(strategies) == set(setup["players"])
    assert all(strategies.values())


def test_chunk_failure_error_envelope(harness):
    submissions = {"team_alpha": VALID_AGENT}
    assert _setup(harness, submissions, requested=10)["status"] == "ok"

    # Force a mid-run explosion; the old task aborted the whole run with this
    # message on any exception from the loop.
    def boom(custom_rewards=None):
        raise RuntimeError("boom")

    harness._state["game"].play_game = boom

    chunk = json.loads(harness.run_chunk_json(3))
    assert set(chunk) == ERROR_ENVELOPE_KEYS
    assert chunk["status"] == "error"
    assert chunk["message"] == "Error running simulations: boom"
