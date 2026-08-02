"""Unit tests for the validation executor (backend/validation_lambda/executor.py).

Direct calls exercise the run body in-process (branch coverage, no fork);
the isolation tests run the real fork/soft-timer/hard-kill machinery with
the module's limit constants monkeypatched short — the forked child inherits
the patch, which is why the executor reads them at call time.
"""

import pytest

from backend.validation_lambda import executor
from backend.validation_lambda.executor import (
    TIMEOUT_MESSAGE,
    ExecutionTimeout,
    run_validation,
    run_validation_isolated,
    timeout_validation_result,
)

VALIDATION_KEYS = {
    "status",
    "message",
    "feedback",
    "simulation_results",
    "duration_ms",
    "traceback",
    "stdout",
}

VALID_CODE = """
from games.prisoners_dilemma.player import Player
import random
import math

class CustomPlayer(Player):
    def make_decision(self, game_state):
        self.add_feedback("Making a decision")
        return 'collude'
"""


@pytest.fixture
def fast_limits(monkeypatch):
    """Shrink the soft/hard limits so timeout-path tests take ~2s, not ~7."""
    monkeypatch.setattr(executor, "VALIDATION_TIMEOUT_SECONDS", 0.5)
    monkeypatch.setattr(executor, "VALIDATION_TIME_LIMIT", 1.5)


def test_timeout_validation_result_shape():
    """The hard-kill fallback dict carries the exact prefix-matched message."""
    result = timeout_validation_result()
    assert result["status"] == "error"
    assert result["message"].startswith("Your agent consumes too much time")
    assert set(result) == VALIDATION_KEYS


# ---------------------------------------------------------------------------
# Direct (in-process) calls.
# ---------------------------------------------------------------------------


def test_run_validation_success_captures_stdout():
    printing_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        print("thinking...")
        return 'collude'
"""
    result = run_validation(
        code=printing_code,
        game_name="prisoners_dilemma",
        team_name="test_team",
    )
    assert result["status"] == "success"
    assert result["duration_ms"] > 0
    assert "strategies" in result["simulation_results"]
    assert "thinking..." in result["stdout"]


def test_run_validation_custom_rewards():
    result = run_validation(
        code=VALID_CODE,
        game_name="prisoners_dilemma",
        team_name="test_team",
        custom_rewards=[4, 0, 6, 2],
    )
    assert result["status"] == "success"


def test_run_validation_soft_limit_chained():
    """The soft limit interrupting an agent call is re-raised by the engine as
    ValueError; the chain walk must still classify the run as a timeout."""
    slow_code = """
from backend.validation_lambda.executor import ExecutionTimeout
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        raise ExecutionTimeout()
"""
    result = run_validation(
        code=slow_code,
        game_name="prisoners_dilemma",
        team_name="test_team",
    )
    assert result["status"] == "error"
    assert result["message"] == TIMEOUT_MESSAGE


def test_run_validation_soft_limit_unwrapped(monkeypatch):
    """An ExecutionTimeout that escapes unwrapped hits its own handler."""

    class TimeoutGame:
        validation_simulations = 5

        def __init__(self, league):
            pass

        def add_player(self, code, name):
            pass

        def run_single_game_with_feedback(self, custom_rewards=None):
            raise ExecutionTimeout()

    import backend.games.game_factory as game_factory

    monkeypatch.setattr(
        game_factory.GameFactory,
        "get_game_class",
        staticmethod(lambda name: TimeoutGame),
    )
    result = run_validation(
        code=VALID_CODE,
        game_name="prisoners_dilemma",
        team_name="test_team",
    )
    assert result["status"] == "error"
    assert result["message"] == TIMEOUT_MESSAGE
    assert result["traceback"] is None


def test_run_validation_invalid_game():
    result = run_validation(
        code=VALID_CODE,
        game_name="invalid_game",
        team_name="test_team",
    )
    assert result["status"] == "error"
    assert "Unknown game" in result["message"]


def test_run_validation_simulation_error():
    """A crashing agent fails validation — no default action is substituted."""
    error_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 1 / 0  # Will cause ZeroDivisionError
"""
    result = run_validation(
        code=error_code,
        game_name="prisoners_dilemma",
        team_name="test_team",
    )
    assert result["status"] == "error"
    assert result["message"].startswith("Error during simulation:")
    assert "Invalid decision by test_team" in result["message"]
    assert "ZeroDivisionError" in result["traceback"]


def test_run_validation_player_feedback():
    feedback_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        self.add_feedback("Testing feedback mechanism")
        return 'collude'
"""
    result = run_validation(
        code=feedback_code,
        game_name="prisoners_dilemma",
        team_name="test_team",
    )
    assert result["status"] == "success"
    assert "feedback" in result
    assert isinstance(result["feedback"], (dict, str))


# ---------------------------------------------------------------------------
# Isolated runs: the real fork / soft-timer / process-group-kill machinery.
# ---------------------------------------------------------------------------


def test_isolated_success():
    result = run_validation_isolated(
        VALID_CODE, "prisoners_dilemma", "test_team"
    )
    assert set(result) == VALIDATION_KEYS
    assert result["status"] == "success"


def test_isolated_spinner_hits_soft_limit(fast_limits):
    """A plain busy loop is interrupted by SIGALRM in the child; the engine
    re-raise is chain-classified and the child itself reports the timeout."""
    spinner = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        while True:
            pass
"""
    result = run_validation_isolated(spinner, "greedy_pig", "spin_team")
    assert result["status"] == "error"
    assert result["message"] == TIMEOUT_MESSAGE


def test_isolated_soft_limit_swallower_is_hard_killed(fast_limits):
    """A busy loop that swallows the soft-limit exception (bare
    ``except Exception``) can only die by the parent's process-group SIGKILL
    — the replacement for Celery's hard time_limit (the old CPU-bomb test)."""
    swallower = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        while True:
            try:
                n = 0
                for i in range(10 ** 8):
                    n += i * i
            except Exception:
                continue
"""
    result = run_validation_isolated(swallower, "greedy_pig", "cpu_bomb_team")
    assert result["status"] == "error"
    assert result["message"] == TIMEOUT_MESSAGE


def test_isolated_runs_do_not_contaminate_each_other():
    """A fresh fork per run (the replacement for worker_max_tasks_per_child=1)
    means one agent's monkeypatching of games.* cannot leak into a later
    validation."""
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
    result = run_validation_isolated(
        contaminating_code, "prisoners_dilemma", "dirty_team"
    )
    assert result["status"] == "success"

    result = run_validation_isolated(
        probe_code, "prisoners_dilemma", "clean_team"
    )
    assert result["status"] == "success"
    assert "CLEAN" in (result.get("stdout") or "")
    assert "CONTAMINATED" not in (result.get("stdout") or "")


def test_isolated_recovers_after_a_killed_run(monkeypatch):
    """After a hard-killed spinner the very next run must still succeed —
    trivially true with a fork per run, but this is the resilience guarantee
    the old worker tests pinned, so keep pinning it."""
    swallower = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        while True:
            try:
                pass
            except Exception:
                continue
"""
    monkeypatch.setattr(executor, "VALIDATION_TIMEOUT_SECONDS", 0.5)
    monkeypatch.setattr(executor, "VALIDATION_TIME_LIMIT", 1.5)
    killed = run_validation_isolated(swallower, "greedy_pig", "bomb_team")
    assert killed["status"] == "error"
    assert killed["message"] == TIMEOUT_MESSAGE

    # Restore the real limits so the probe has its full budget.
    monkeypatch.setattr(executor, "VALIDATION_TIMEOUT_SECONDS", 5)
    monkeypatch.setattr(executor, "VALIDATION_TIME_LIMIT", 6)
    probe = (
        "from games.greedy_pig.player import Player\n"
        "class CustomPlayer(Player):\n"
        "    def make_decision(self, game_state):\n"
        "        return 'bank'\n"
    )
    result = run_validation_isolated(probe, "greedy_pig", "recovery_team")
    assert result["status"] == "success", result
