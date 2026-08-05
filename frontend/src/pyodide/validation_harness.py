"""The in-browser agent-validation harness, run inside Pyodide.

Replicates the semantics of the server validation executor
(backend/lambda_fallback/validation/executor.py::run_validation): construct the game with
its validation bots, add the submitted player, one verbose feedback game,
then the game's benchmarked ``validation_simulations`` pass, returning the
same 7-key ValidationResponse dict. The error messages reuse the task's
exact phrasing because backend/routes/ai/hint_context.py prefix-matches
them. Parity with the task running under CPython is enforced by
backend/tests/unit/test_validation_harness_parity.py, which execs this exact
file in the test container.

Two deliberate deltas from the task:

- ``League`` (a SQLModel) is replaced by a ``SimpleNamespace`` — games only
  ever read attributes off the league object (same substitution as
  simulation_harness.py).
- The ``SoftTimeLimitExceeded`` handling is gone: Pyodide has no signals, so
  nothing can interrupt running agent code in-harness. Timeouts are the JS
  client's job — validationRunnerClient.js terminates the whole worker at
  its watchdog budget and synthesizes the timeout envelope itself.

``probe_validation_json`` is the health check: it validates the game's own
``starter_code`` (read off the game class already on the filesystem — no
network, nothing leaves the browser). A runtime that can't validate starter
code can't be trusted with real submissions, so the client routes them to
the server fallback.

Each bridge function returns a JSON string serialized inside Python so only
a plain ``str`` crosses the JS bridge (no PyProxy issues; same rule as the
other harnesses). Environment contract: ``backend.games.*`` must be
importable — natively true under CPython in the test container; in the
browser the validation worker first writes the engine copies
(frontend/src/pyodide/games/) onto Pyodide's filesystem and puts their root
on ``sys.path``. Must stay stdlib-only: Pyodide loads no wheels.
"""

import contextlib
import io
import json
import time
import traceback as tb
from types import SimpleNamespace
from typing import Any, Dict, Optional


def _normalize(result: Dict[str, Any]) -> Dict[str, Any]:
    """The full 7-key ValidationResponse shape consumers expect."""
    return {
        "status": result.get("status", "error"),
        "message": result.get("message"),
        "feedback": result.get("feedback"),
        "simulation_results": result.get("simulation_results"),
        "duration_ms": result.get("duration_ms"),
        "traceback": result.get("traceback"),
        "stdout": result.get("stdout"),
    }


def run_validation(
    code: str,
    game_name: str,
    team_name: str,
    custom_rewards: Optional[list] = None,
) -> Dict[str, Any]:
    """Run the full validation load and return the ValidationResponse dict."""
    from backend.games.base_game import PlayerConstructionError
    from backend.games.game_factory import GameFactory

    buf = io.StringIO()
    result: Dict[str, Any]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            test_league = SimpleNamespace(
                id=0, name="validation_leagueX", game=game_name
            )
            game_class = GameFactory.get_game_class(game_name)
            game_instance = game_class(test_league)
            game_instance.add_player(code, team_name)
            t0 = time.perf_counter()
            feedback_result = game_instance.run_single_game_with_feedback(
                custom_rewards
            )
            game_instance.reset()
            # Each game declares its own validation pass count, benchmarked
            # so the whole load stays under one second (on the server; the
            # browser wears its Pyodide slowdown against the JS watchdog).
            simulation_results = game_instance.run_simulations(
                game_class.validation_simulations, test_league, custom_rewards
            )
            simulation_results["strategies"] = (
                game_instance.get_player_strategies()
            )
            result = {
                "status": "success",
                "feedback": feedback_result.get("feedback"),
                "simulation_results": simulation_results,
                "duration_ms": (time.perf_counter() - t0) * 1000,
            }
    except PlayerConstructionError as e:
        result = {
            "status": "error",
            "message": f"Failed to create player for team {team_name}: {e}",
            "traceback": e.traceback_str,
        }
    except Exception as e:  # noqa: BLE001 - the harness boundary is the catch-all
        result = {
            "status": "error",
            "message": f"Error during simulation: {str(e)}",
            "traceback": tb.format_exc(),
        }
    captured = buf.getvalue()
    if captured.strip():
        result["stdout"] = captured
    return _normalize(result)


def run_validation_json(game_name: str, code: str, team_name: str) -> str:
    return json.dumps(run_validation(code, game_name, team_name))


def probe_validation_json(game_name: str) -> str:
    """Validate the game's own starter code — the local health check."""
    from backend.games.game_factory import GameFactory

    try:
        starter_code = GameFactory.get_game_class(game_name).starter_code
    except Exception as e:  # noqa: BLE001 - unknown game = failed probe
        return json.dumps(
            _normalize({"status": "error", "message": str(e)})
        )
    return json.dumps(run_validation(starter_code, game_name, "Starter"))
