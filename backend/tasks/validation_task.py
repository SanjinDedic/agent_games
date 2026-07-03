"""The Celery validation task and its enqueue/await helpers.

The AST safety check (backend/routes/user/code_validation.py) runs in the API
process before enqueue — unsafe code never reaches a worker. The run_validation
task executes the agent inside a worker child process;
worker_max_tasks_per_child=1 gives every task a fresh process, so a
monkeypatching or crashing agent cannot contaminate later runs.

The error message strings here are prefix-matched by
backend/routes/ai/hint_context.py (classify_outcome) — do not reword them.
"""

import contextlib
import io
import time
import traceback as tb
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from billiard.exceptions import WorkerLostError
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded

from backend.database.db_models import League
from backend.games.game_factory import GameFactory
from backend.tasks.celery_app import celery_app
from backend.tasks.celery_utils import poll_task_result

# Universal hard cap for agent validation (single game + simulations).
VALIDATION_TIMEOUT_SECONDS = 5

# How long the API waits for a validation result before giving up (and killing
# the task). Above the 6s hard task limit so a legitimately slow validation
# still returns, but bounded so a queue backlog can't hang a request.
VALIDATION_RESULT_TIMEOUT = 6

# Drop a queued validation whose submitter has already stopped waiting, so a
# flood of submissions cannot build an unbounded backlog that starves live ones
# (the workers keep churning tasks nobody is waiting for otherwise).
VALIDATION_TASK_EXPIRES = 8

# Prefix-matched by hint_context.classify_outcome — do not reword. Shared by
# the task's soft-limit handler and the routers' hard-kill fallback.
TIMEOUT_MESSAGE = (
    f"Your agent consumes too much time - validation did not "
    f"finish within {VALIDATION_TIMEOUT_SECONDS} seconds. "
    f"The agent may be too slow or stuck in a loop."
)


def _normalize(result: Dict[str, Any]) -> Dict[str, Any]:
    """Return the full 7-key ValidationResponse shape consumers expect."""
    return {
        "status": result.get("status", "error"),
        "message": result.get("message"),
        "feedback": result.get("feedback"),
        "simulation_results": result.get("simulation_results"),
        "duration_ms": result.get("duration_ms"),
        "traceback": result.get("traceback"),
        "stdout": result.get("stdout"),
    }


def timeout_validation_result() -> Dict[str, Any]:
    """ValidationResponse dict for a hard-killed (timed-out) validation task."""
    return _normalize({"status": "error", "message": TIMEOUT_MESSAGE})


def enqueue_validation(
    code: str,
    game_name: str,
    team_name: str,
    num_simulations: int = 20,
    custom_rewards: Optional[list] = None,
):
    """Enqueue a validation task that self-drops if it waits out its usefulness.

    `expires` means a task still queued after VALIDATION_TASK_EXPIRES seconds is
    discarded instead of run — the submitter has long since given up, so running
    it would only burn a worker slot and deepen a backlog.
    """
    return run_validation.apply_async(
        kwargs={
            "code": code,
            "game_name": game_name,
            "team_name": team_name,
            "num_simulations": num_simulations,
            "custom_rewards": custom_rewards,
        },
        expires=VALIDATION_TASK_EXPIRES,
    )


async def await_validation_result(
    async_result, timeout: float = VALIDATION_RESULT_TIMEOUT
) -> Dict[str, Any]:
    """Await a validation task and always return a normalized ValidationResponse.

    Polls the result backend (no blocking .get(), no shared pubsub consumer to
    corrupt under concurrency). A worker killed by the hard time limit (spin/CPU)
    or by an OOM SIGKILL, and a task that outlives the caller's patience, all map
    to the same user-facing "consumes too much time" failure — the job is
    discarded (acks_late=False → never redelivered), not retried.
    """
    try:
        return await poll_task_result(async_result, timeout)
    except (TimeLimitExceeded, WorkerLostError, TimeoutError):
        return timeout_validation_result()
    except Exception as e:  # noqa: BLE001 - any task fault becomes a clean error
        return _normalize(
            {"status": "error", "message": f"Error during validation: {e}"}
        )


@celery_app.task(
    name="validation.run",
    soft_time_limit=VALIDATION_TIMEOUT_SECONDS,
    # Hard SIGKILL backstop, kept tight (1s past the soft limit): the game engine
    # and agents with a bare `except Exception` swallow SoftTimeLimitExceeded, so
    # only this hard kill reliably reaps a spinner — a wide gap just lets a
    # runaway agent hold a worker core longer (CPU is the binding constraint).
    time_limit=6,
)
def run_validation(
    code: str,
    game_name: str,
    team_name: str,
    num_simulations: int = 100,
    custom_rewards: Optional[list] = None,
) -> Dict[str, Any]:
    """Run the full validation load and return the ValidationResponse dict."""
    buf = io.StringIO()
    result: Dict[str, Any]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            test_league = League(
                name="validation_leagueX",
                created_date=datetime.now(),
                expiry_date=datetime.now() + timedelta(days=1),
                game=game_name,
            )
            game_class = GameFactory.get_game_class(game_name)
            game_instance = game_class(test_league)
            player = game_instance.add_player(code, team_name)
            if player is None:
                result = {
                    "status": "error",
                    "message": f"Failed to create player for team {team_name}",
                }
            else:
                t0 = time.perf_counter()
                feedback_result = game_instance.run_single_game_with_feedback(
                    custom_rewards
                )
                game_instance.reset()
                simulation_results = game_instance.run_simulations(
                    num_simulations, test_league, custom_rewards
                )
                result = {
                    "status": "success",
                    "feedback": feedback_result.get("feedback"),
                    "simulation_results": simulation_results,
                    "duration_ms": (time.perf_counter() - t0) * 1000,
                }
    except SoftTimeLimitExceeded:
        # Only reached when nothing swallowed the exception. Game engines wrap
        # agent calls in `except Exception`, which eats this too — those runs
        # spin on until the hard time_limit SIGKILL, and the routers map the
        # resulting TimeLimitExceeded to the same message.
        result = {
            "status": "error",
            "message": TIMEOUT_MESSAGE,
        }
    except Exception as e:  # noqa: BLE001 - the task boundary is the catch-all
        result = {
            "status": "error",
            "message": f"Error during simulation: {str(e)}",
            "traceback": tb.format_exc(),
        }
    captured = buf.getvalue()
    if captured.strip():
        result["stdout"] = captured
    return _normalize(result)
