"""Agent exceptions must surface to the AI hint context as stack traces.

Two delivery paths out of run_validation (called directly here — no worker
needed, we only exercise trace capture, not timeouts/isolation):

1. Abort-on-error games (lineup4, hearts, ohhell, thirteen) re-raise the agent
   exception as ValueError; the task boundary formats the *chained* traceback,
   so the agent's own frames are included -> status "error" + traceback.
2. Swallow-and-default games (greedy_pig, prisoners_dilemma, arena_champions)
   keep playing; they record each distinct trace via
   BaseGame.record_error_trace and run_validation attaches them
   -> status "success" + traceback.

Construction failures (exec / __init__ raising) surface via
PlayerConstructionError -> "Failed to create player..." + traceback.
"""

from backend.games.base_game import MAX_ERROR_TRACES
from backend.routes.ai.hint_context import HintContext
from backend.tasks.validation_task import run_validation


def _crashing_agent(game: str, method: str = "make_decision") -> str:
    return f"""
from games.{game}.player import Player

class CustomPlayer(Player):
    def {method}(self, *args, **kwargs):
        raise RuntimeError("agent exploded")
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
    return run_validation(
        code=code, game_name=game, team_name="CrashTeam", num_simulations=2
    )


# --- Swallow-and-default games: game succeeds, traces still delivered --------


def _assert_success_with_trace(result: dict, method: str):
    assert result["status"] == "success"
    assert result["traceback"] is not None
    assert f"CrashTeam.{method}" in result["traceback"]
    assert "RuntimeError: agent exploded" in result["traceback"]
    # The agent's own frame (exec'd code compiles as "<string>").
    assert '"<string>"' in result["traceback"]


def test_greedy_pig_swallowed_crash_delivers_trace():
    result = _validate(_crashing_agent("greedy_pig"), "greedy_pig")
    _assert_success_with_trace(result, "make_decision")
    # The pre-existing print() still lands in captured stdout.
    assert "Error in player CrashTeam's decision" in result["stdout"]


def test_prisoners_dilemma_swallowed_crash_delivers_trace():
    result = _validate(_crashing_agent("prisoners_dilemma"), "prisoners_dilemma")
    _assert_success_with_trace(result, "make_decision")


def test_arena_champions_swallowed_crash_delivers_trace():
    code = _crashing_agent("arena_champions", "make_combat_decision")
    result = _validate(code, "arena_champions")
    _assert_success_with_trace(result, "make_combat_decision")


def test_traces_are_deduplicated_and_capped():
    # Crashes identically every turn of every simulation: one recorded trace.
    result = _validate(_crashing_agent("greedy_pig"), "greedy_pig")
    traces = result["traceback"].split("[CrashTeam.make_decision]")
    assert len(traces) - 1 <= MAX_ERROR_TRACES
    assert result["traceback"].count("RuntimeError: agent exploded") <= MAX_ERROR_TRACES


# --- Abort-on-error games: chained traceback at the task boundary ------------


def test_lineup4_crash_delivers_chained_trace():
    result = _validate(_crashing_agent("lineup4"), "lineup4")
    assert result["status"] == "error"
    assert result["message"].startswith("Error during simulation:")
    assert "Invalid move by CrashTeam" in result["message"]
    # Chained traceback keeps the agent's original frames.
    assert "RuntimeError: agent exploded" in result["traceback"]
    assert "During handling of the above exception" in result["traceback"]
    assert '"<string>"' in result["traceback"]


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


# --- Hint context integration -------------------------------------------------


def test_hint_context_renders_trace_for_swallowed_crash():
    code = _crashing_agent("greedy_pig")
    result = _validate(code, "greedy_pig")
    ctx = HintContext.from_validation_response(
        code, result, game_name="greedy_pig", team_name="CrashTeam",
        include_game_code=False,
    )
    assert ctx.category == "success"
    rendered = str(ctx)
    assert "--- Stack Trace ---" in rendered
    assert "swallowed these agent exceptions" in rendered
    assert "RuntimeError: agent exploded" in rendered


def test_hint_context_renders_trace_for_construction_error():
    result = _validate(CONSTRUCTION_CRASH, "greedy_pig")
    ctx = HintContext.from_validation_response(
        CONSTRUCTION_CRASH, result, game_name="greedy_pig",
        team_name="CrashTeam", include_game_code=False,
    )
    assert ctx.category == "construction_error"
    rendered = str(ctx)
    assert "--- Stack Trace ---" in rendered
    assert "ZeroDivisionError" in rendered


def test_hint_context_renders_trace_for_runtime_error():
    code = _crashing_agent("lineup4")
    result = _validate(code, "lineup4")
    ctx = HintContext.from_validation_response(
        code, result, game_name="lineup4", team_name="CrashTeam",
        include_game_code=False,
    )
    assert ctx.category == "runtime_error"
    rendered = str(ctx)
    assert "--- Stack Trace ---" in rendered
    assert "RuntimeError: agent exploded" in rendered
