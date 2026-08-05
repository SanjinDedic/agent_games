"""Agent exceptions must surface in the envelope as stack traces.

Every game aborts on a bad agent: an exception (or an invalid return value)
in the agent's decision method is re-raised as ValueError, and the task
boundary formats the *chained* traceback, so the agent's own frames are
included -> status "error" + traceback. No game substitutes a default action.

run_validation is called directly here — we only exercise trace capture,
not timeouts/isolation.

Construction failures (exec / __init__ raising) surface via
PlayerConstructionError -> "Failed to create player..." + traceback.

The rendering of these envelopes into the hint prompt is pinned publicly in
backend/tests/unit/routes/ai/test_hint_context.py against envelope literals.
"""

import pytest

from backend.validation_lambda.executor import run_validation


def _crashing_agent(game: str, method: str = "make_decision") -> str:
    return f"""
from games.{game}.player import Player

class CustomPlayer(Player):
    def {method}(self, *args, **kwargs):
        raise RuntimeError("agent exploded")
"""


def _invalid_return_agent(game: str, method: str = "make_decision") -> str:
    return f"""
from games.{game}.player import Player

class CustomPlayer(Player):
    def {method}(self, *args, **kwargs):
        return "hoard"
"""


CONSTRUCTION_CRASH = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def __init__(self):
        super().__init__()
        self.ratio = 1 / 0

    def make_decision(self, game_state):
        return "bank"
"""


def _validate(code: str, game: str) -> dict:
    return run_validation(code=code, game_name=game, team_name="CrashTeam")


# --- Crashing agents abort every game: chained traceback at the task boundary


# (game, decision method, wording of the engine's ValueError)
GAME_CASES = [
    ("greedy_pig", "make_decision", "Invalid decision by CrashTeam"),
    ("prisoners_dilemma", "make_decision", "Invalid decision by CrashTeam"),
    ("arena_champions", "make_combat_decision", "Invalid action by CrashTeam"),
    ("breakthrough", "make_decision", "Invalid move by CrashTeam"),
    ("lineup4", "make_decision", "Invalid move by CrashTeam"),
]


@pytest.mark.parametrize("game,method,error_prefix", GAME_CASES)
def test_crashing_agent_aborts_with_chained_trace(game, method, error_prefix):
    result = _validate(_crashing_agent(game, method), game)
    assert result["status"] == "error"
    assert result["message"].startswith("Error during simulation:")
    assert error_prefix in result["message"]
    # Chained traceback keeps the agent's original frames (exec'd code
    # compiles as "<string>").
    assert "RuntimeError: agent exploded" in result["traceback"]
    assert "During handling of the above exception" in result["traceback"]
    assert '"<string>"' in result["traceback"]


@pytest.mark.parametrize("game,method,error_prefix", GAME_CASES)
def test_invalid_return_aborts(game, method, error_prefix):
    result = _validate(_invalid_return_agent(game, method), game)
    assert result["status"] == "error"
    assert result["message"].startswith("Error during simulation:")
    assert error_prefix in result["message"]


# --- Construction failures ----------------------------------------------------


def test_construction_crash_delivers_trace():
    result = _validate(CONSTRUCTION_CRASH, "greedy_pig")
    assert result["status"] == "error"
    assert result["message"].startswith("Failed to create player for team CrashTeam")
    assert "ZeroDivisionError" in result["message"]
    assert "ZeroDivisionError" in result["traceback"]


def test_missing_custom_player_has_message_but_no_trace():
    result = _validate("x = 1", "greedy_pig")
    assert result["status"] == "error"
    assert result["message"].startswith("Failed to create player for team CrashTeam")
    assert "No CustomPlayer class" in result["message"]
    assert result["traceback"] is None
