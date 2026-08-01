"""The in-browser league-simulation harness, run inside Pyodide.

Replicates the semantics of the deleted Celery simulation task
(backend/tasks/simulation_task.py at its final revision): player loading with
skip-on-construction-error, one verbose feedback game up front, then plain
``reset()``/``play_game()`` runs whose points are aggregated exactly like the
old ``aggregate_simulation_results`` (points summed per player, ``table``
taken from the last completed game, ``{}`` when the game reports none). The
error envelopes reuse the task's exact message phrasing so the frontend
surfaces identical text. Structural parity with the game engine running under
CPython is enforced by backend/tests/unit/test_simulation_harness_parity.py,
which execs this exact file in the test container.

The run is split into three bridge calls so the JS side can chunk the work —
progress and cancellation are only observable between synchronous Python
calls (no SharedArrayBuffer interrupt without COOP/COEP headers):

- ``setup_run_json``: build the game, load players, play the feedback game.
- ``run_chunk_json``: play up to N games, accumulating points.
- ``finalize_json``: return the old task's full success envelope.

Each returns a JSON string serialized inside Python so only a plain ``str``
crosses the JS bridge (no PyProxy issues; same rule as exercise_harness.py).

Environment contract: ``backend.games.*`` must be importable — natively true
under CPython in the test container; in the browser the simulation worker
first writes the engine copies (frontend/src/pyodide/games/) onto Pyodide's
filesystem and puts their root on ``sys.path``. Must stay stdlib-only:
Pyodide loads no wheels for simulations.
"""

import json
from types import SimpleNamespace
from typing import Any, Dict, Optional

# Populated by setup_run_json; one run at a time per interpreter (the JS
# client serializes runs, and a cancelled run's worker is terminated whole).
_state: Dict[str, Any] = {}


def _error_envelope(message: str, requested_simulations: int) -> Dict[str, Any]:
    """The old task's error shape, verbatim."""
    return {
        "status": "error",
        "message": message,
        "simulation_results": {
            "total_points": {},
            "num_simulations": requested_simulations,
            "table": {},
        },
    }


def setup_run(
    game_name: str,
    submissions: Optional[Dict[str, str]],
    custom_rewards: Optional[list],
    requested_simulations: int,
) -> Dict[str, Any]:
    """Build the game, load players, and play the one verbose feedback game.

    Mirrors the old task's _load_submitted_players: an empty submissions map
    keeps the game's built-in validation players; a submission whose code
    fails to construct is skipped, not fatal — but here the failures are
    returned to the caller instead of only being logged server-side.
    """
    from backend.games.game_factory import GameFactory

    # The old task built a transient SQLModel League row purely to satisfy the
    # game constructor; games only ever store it, so a namespace is enough
    # (SQLModel is not importable in the browser).
    league = SimpleNamespace(id=0, name="simulation_league", game=game_name)

    game_class = GameFactory.get_game_class(game_name)
    game = game_class(league)

    skipped = []
    if submissions:
        game.players = []
        game.scores = {}
        for team_name, code in submissions.items():
            try:
                game.add_player(code, team_name)
            except Exception as e:  # noqa: BLE001 — mirror task: skip, don't die
                skipped.append({"team": team_name, "error": str(e)})

    if not game.players:
        return _error_envelope(
            "No players loaded for simulation", requested_simulations
        )

    try:
        feedback_result = game.run_single_game_with_feedback(custom_rewards)
    except Exception as e:  # noqa: BLE001 — same catch-all as the task
        return _error_envelope(
            f"Error running feedback game: {str(e)}", requested_simulations
        )

    _state.clear()
    _state.update(
        {
            "game": game,
            "custom_rewards": custom_rewards,
            "requested_simulations": requested_simulations,
            "feedback": feedback_result["feedback"],
            "player_feedback": feedback_result["player_feedback"],
            "total_points": {},
            "table": {},
            "runs_attempted": 0,
            "skipped": skipped,
        }
    )

    return {
        "status": "ok",
        "players": [str(p.name) for p in game.players],
        "skipped": skipped,
    }


def run_chunk(count: int) -> Dict[str, Any]:
    """Play up to ``count`` games, accumulating the aggregate incrementally.

    Point sums and the keep-only-the-last ``table`` reproduce the old
    aggregate_simulation_results without storing thousands of result dicts.
    """
    game = _state["game"]
    custom_rewards = _state["custom_rewards"]
    total_points = _state["total_points"]

    try:
        for _ in range(count):
            game.reset()
            result = game.play_game(custom_rewards)
            _state["runs_attempted"] += 1
            if result is None:
                continue
            if "points" in result:
                for player, points in result["points"].items():
                    total_points[player] = total_points.get(player, 0) + points
            _state["table"] = result["table"] if "table" in result else {}
    except Exception as e:  # noqa: BLE001 — same catch-all as the task
        return _error_envelope(
            f"Error running simulations: {str(e)}",
            _state["requested_simulations"],
        )

    return {"status": "ok", "completed": _state["runs_attempted"]}


def finalize(capped: bool) -> Dict[str, Any]:
    """The old task's success envelope, plus the skipped-team list."""
    game = _state["game"]
    return {
        "status": "success",
        "feedback": _state["feedback"],
        "player_feedback": _state["player_feedback"],
        "simulation_results": {
            "total_points": _state["total_points"],
            "num_simulations": _state["runs_attempted"],
            "table": _state["table"],
            "requested_simulations": _state["requested_simulations"],
            "capped": capped,
            # Only validation players declare a strategy, so this is empty
            # whenever real league submissions replaced them.
            "strategies": game.get_player_strategies(),
        },
        "skipped": _state["skipped"],
    }


def setup_run_json(
    game_name: str,
    submissions_json: str,
    custom_rewards_json: str,
    requested_simulations: int,
) -> str:
    return json.dumps(
        setup_run(
            game_name,
            json.loads(submissions_json) if submissions_json else None,
            json.loads(custom_rewards_json) if custom_rewards_json else None,
            requested_simulations,
        )
    )


def run_chunk_json(count: int) -> str:
    return json.dumps(run_chunk(count))


def finalize_json(capped: bool) -> str:
    return json.dumps(finalize(capped))
