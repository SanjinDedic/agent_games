"""Parity contract between the server validation executor and the browser
harness.

The in-browser validation runner (frontend/src/pyodide/validation_harness.py)
is an extraction of backend/validation_lambda/executor.py::run_validation:
same game load, same envelope, same error phrasing (which hint_context
prefix-matches). Students must get identical results whether their agent
validates in Pyodide or falls back to the server. These tests exec the exact
file the browser ships under CPython — where ``backend.games`` imports
natively, no filesystem shim needed — and compare it against the executor on
shared fixtures.

Games are stochastic (they reseed per roll/hand), so success parity is
structural: same key sets, same participants, same simulation count. Error
parity is exact on status and message, with tracebacks reduced to the frames
inside the agent's exec'd code plus the final exception line.

``test_starter_code_validates_for_every_game`` is the server-side guarantee
behind the browser health probe: the probe validates the game's own
starter_code locally, so starter code that stops validating must fail CI,
not silently push every student onto the server fallback.

The harness file reaches the test container through the read-only
frontend/src/pyodide volume in docker-compose.yml.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from backend.config import GAMES
from backend.games.game_factory import GameFactory
from backend.validation_lambda import executor as validation_executor

HARNESS_PATH = (
    Path(__file__).resolve().parents[3]
    / "frontend"
    / "src"
    / "pyodide"
    / "validation_harness.py"
)

ENVELOPE_KEYS = {
    "status",
    "message",
    "feedback",
    "simulation_results",
    "duration_ms",
    "traceback",
    "stdout",
}


def _load_harness():
    spec = importlib.util.spec_from_file_location(
        "validation_harness", HARNESS_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


harness = _load_harness()


def _normalize_traceback(traceback_text):
    """The comparable part of a traceback: the frames inside the agent's
    exec'd code plus the final exception line. Frames pointing into
    executor.py vs validation_harness.py legitimately differ."""
    if traceback_text is None:
        return None
    lines = traceback_text.rstrip("\n").split("\n")
    kept = [line for line in lines if '"<string>"' in line]
    kept.append(lines[-1])
    return kept


def _run_both(code, game_name, team_name):
    """Run one fixture through the executor (called inline) and the harness;
    assert shared structure and return the pair."""
    task_result = validation_executor.run_validation(
        code=code, game_name=game_name, team_name=team_name
    )
    harness_result = json.loads(
        harness.run_validation_json(game_name, code, team_name)
    )

    for result in (task_result, harness_result):
        assert set(result) == ENVELOPE_KEYS
        if result["duration_ms"] is not None:
            assert isinstance(result["duration_ms"], float)

    assert task_result["status"] == harness_result["status"]
    assert task_result["message"] == harness_result["message"]
    assert _normalize_traceback(task_result["traceback"]) == (
        _normalize_traceback(harness_result["traceback"])
    )
    return task_result, harness_result


def _assert_success_parity(task_result, harness_result, team_name):
    """Structural equivalence for stochastic success envelopes."""
    task_sim = task_result["simulation_results"]
    harness_sim = harness_result["simulation_results"]
    assert set(task_sim) == set(harness_sim)
    assert task_sim["num_simulations"] == harness_sim["num_simulations"]
    assert set(task_sim["total_points"]) == set(harness_sim["total_points"])
    assert team_name in harness_sim["total_points"]
    assert set(task_sim["strategies"]) == set(harness_sim["strategies"])
    assert type(task_result["feedback"]) is type(harness_result["feedback"])


@pytest.mark.parametrize("game_name", sorted(GAMES))
def test_starter_code_validates_for_every_game(game_name):
    starter_code = GameFactory.get_game_class(game_name).starter_code
    task_result, harness_result = _run_both(starter_code, game_name, "Starter")
    assert task_result["status"] == "success", task_result["message"]
    _assert_success_parity(task_result, harness_result, "Starter")


def test_probe_entry_point_matches_run_validation_shape():
    envelope = json.loads(harness.probe_validation_json("greedy_pig"))
    assert set(envelope) == ENVELOPE_KEYS
    assert envelope["status"] == "success", envelope["message"]
    assert "Starter" in envelope["simulation_results"]["total_points"]


def test_probe_unknown_game_is_an_error_envelope():
    envelope = json.loads(harness.probe_validation_json("no_such_game"))
    assert set(envelope) == ENVELOPE_KEYS
    assert envelope["status"] == "error"
    assert envelope["message"]


def test_missing_custom_player_construction_error_parity():
    code = "from games.greedy_pig.player import Player\n"
    task_result, _ = _run_both(code, "greedy_pig", "team_x")
    assert task_result["status"] == "error"
    assert task_result["message"].startswith(
        "Failed to create player for team team_x:"
    )


def test_syntax_error_construction_error_parity():
    code = "def broken(:\n"
    task_result, _ = _run_both(code, "greedy_pig", "team_x")
    assert task_result["status"] == "error"
    assert task_result["message"].startswith(
        "Failed to create player for team team_x:"
    )


def test_agent_runtime_crash_parity():
    code = (
        "from games.greedy_pig.player import Player\n"
        "class CustomPlayer(Player):\n"
        "    def make_decision(self, game_state):\n"
        "        return 1 / 0\n"
    )
    task_result, harness_result = _run_both(code, "greedy_pig", "test_team")
    assert task_result["status"] == "error"
    assert task_result["message"].startswith("Error during simulation:")
    assert "division by zero" in task_result["message"]
    assert "ZeroDivisionError" in harness_result["traceback"]


def test_stdout_captured_and_omitted_when_blank():
    printing = (
        "from games.greedy_pig.player import Player\n"
        "print('hello from agent')\n"
        "class CustomPlayer(Player):\n"
        "    def make_decision(self, game_state):\n"
        "        return 'continue' if game_state['unbanked_money'][self.name] < 20 else 'bank'\n"
    )
    task_result, harness_result = _run_both(printing, "greedy_pig", "team_x")
    assert task_result["status"] == "success"
    assert "hello from agent" in harness_result["stdout"]

    silent = printing.replace("print('hello from agent')\n", "")
    _, harness_silent = _run_both(silent, "greedy_pig", "team_x")
    assert harness_silent["stdout"] is None


def test_harness_has_no_celery_or_sqlmodel_dependency():
    # A missing volume mount should fail loudly, not skip.
    assert HARNESS_PATH.is_file(), f"harness not mounted at {HARNESS_PATH}"
    source = HARNESS_PATH.read_text()
    for forbidden in ("import celery", "from celery", "sqlmodel", "db_models"):
        assert forbidden not in source, (
            f"validation_harness.py must stay stdlib-only but mentions "
            f"{forbidden!r}"
        )
