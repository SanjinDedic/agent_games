"""Execution core for server-side agent validation — celery-free.

Ported near line-for-line from the retired Celery task
(the deleted backend/tasks/validation_task.py::run_validation) so the parity
test keeps pinning these semantics against the browser-shipped Pyodide
harness (frontend/src/pyodide/validation_harness.py). Unlike the exercise fallback
(backend/fallback_lambda/, destined for deletion), this module is permanent
infra: hint generation always needs a fresh server-run envelope, so the
server-side validator can never move to the browser.

The only imports beyond the stdlib are ``backend.games.*`` (which the Lambda
zip ships) and, transitively, ``backend.config`` — satisfied inside the zip
by a generated stdlib-only stub (see deploy.sh) and in the local subprocess
by the ``sys.modules`` stub local_run.py installs. Nothing here may import
sqlmodel, celery, boto3, or dotenv.

Agent code arrives pre-gated by the AST safety check
(backend/routes/user/code_validation.py) in the API process — that gate is
unchanged. The sandbox is still real: no secrets, no DB or S3 connection,
and ``run_validation_isolated`` gives every run a fresh forked child, so one
submission cannot contaminate the next even on a warm Lambda container
(the old worker's ``worker_max_tasks_per_child=1``).

Time limits reproduce the old Celery pair exactly:

- soft 5s — SIGALRM in the child raises :class:`ExecutionTimeout` at the
  current instruction, which maps to the timeout envelope. Like Celery's
  SoftTimeLimitExceeded it is an ``Exception`` subclass on purpose: agent
  code with a bare ``except Exception`` swallows it, and only the hard kill
  reliably reaps a spinner.
- hard 6s — the parent SIGKILLs the child's whole process group
  (``setsid`` + ``killpg``, so fork-bomb descendants die too) and returns
  the same timeout envelope.

The error message strings here are prefix-matched by
backend/routes/ai/hint_context.py (classify_outcome) — do not reword them.
"""

import contextlib
import io
import json
import multiprocessing
import os
import signal
import time
import traceback as tb
from types import SimpleNamespace
from typing import Any, Dict, Optional


class ExecutionTimeout(Exception):
    """Soft-limit signal, stand-in for Celery's SoftTimeLimitExceeded.

    Deliberately an ``Exception`` subclass for exact behavioral parity with
    the old worker: agent code that catches ``Exception`` swallows it and
    spins on until the hard kill, same as before.
    """


# Universal cap for agent validation (single game + simulations; each game's
# validation_simulations count is benchmarked to keep the whole load under a
# second, so 5s is generous). Plain constants, not env-overridable: a
# constant cannot drift between the API client and the deployed Lambda.
# Tests that need a short limit monkeypatch these module globals before
# calling run_validation_isolated — the forked child inherits the patch.
VALIDATION_TIMEOUT_SECONDS = 5

# Hard SIGKILL backstop, always 1s past the soft limit: agents with a bare
# `except Exception` swallow ExecutionTimeout, so only the hard kill
# reliably reaps a spinner — a wide gap just lets a runaway agent hold the
# CPU longer (CPU is the binding constraint).
VALIDATION_TIME_LIMIT = VALIDATION_TIMEOUT_SECONDS + 1

# Prefix-matched by hint_context.classify_outcome — do not reword. Shared by
# the soft-limit handler here and the client's hard-kill collapse.
TIMEOUT_MESSAGE = (
    f"Your agent consumes too much time - validation did not "
    f"finish within {VALIDATION_TIMEOUT_SECONDS} seconds. "
    f"The agent may be too slow or stuck in a loop."
)


def _soft_limit_in_chain(exc: Optional[BaseException]) -> bool:
    """True when the soft time limit is anywhere in the exception chain.

    Game engines re-raise agent exceptions as ValueError; when the agent was
    interrupted by ExecutionTimeout, the original exception survives as
    ``__cause__``/``__context__`` and the run must be reported as a timeout,
    not as a bug in the agent.
    """
    seen: set = set()
    while exc is not None and id(exc) not in seen:
        if isinstance(exc, ExecutionTimeout):
            return True
        seen.add(id(exc))
        exc = exc.__cause__ or exc.__context__
    return False


def normalize_result(result: Dict[str, Any]) -> Dict[str, Any]:
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
    """ValidationResponse dict for a hard-killed (timed-out) validation run."""
    return normalize_result({"status": "error", "message": TIMEOUT_MESSAGE})


def run_validation(
    code: str,
    game_name: str,
    team_name: str,
    custom_rewards: Optional[list] = None,
) -> Dict[str, Any]:
    """Run the full validation load and return the ValidationResponse dict.

    Direct call = no time limit (unit tests, parity test). Production paths
    go through :func:`run_validation_isolated`, which forks and arms the
    soft timer before calling this.
    """
    # Lazy imports keep this module importable for its constants (the API
    # client needs TIMEOUT_MESSAGE) without dragging the games tree along.
    from backend.games.base_game import PlayerConstructionError
    from backend.games.game_factory import GameFactory

    buf = io.StringIO()
    result: Dict[str, Any]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            # Games only ever store the league object, so a SimpleNamespace
            # stands in for the SQLModel League — same substitution the
            # browser harness makes (validation_harness.py).
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
            # so the whole load stays under one second.
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
    except ExecutionTimeout:
        # Only reached when nothing swallowed the exception. An agent with a
        # bare `except Exception` eats this too — those runs spin on until
        # the hard kill, which the parent maps to the same message.
        result = {
            "status": "error",
            "message": TIMEOUT_MESSAGE,
        }
    except Exception as e:  # noqa: BLE001 - the run boundary is the catch-all
        if _soft_limit_in_chain(e):
            # The soft limit fired inside an agent call and the engine
            # re-raised it as ValueError — a slow agent, not a buggy one.
            result = {"status": "error", "message": TIMEOUT_MESSAGE}
        else:
            # The escaping exception's traceback is chained (games re-raise
            # agent exceptions as ValueError inside `except` blocks, so the
            # agent's own frames are included).
            result = {
                "status": "error",
                "message": f"Error during simulation: {str(e)}",
                "traceback": tb.format_exc(),
            }
    captured = buf.getvalue()
    if captured.strip():
        result["stdout"] = captured
    return normalize_result(result)


# ---------------------------------------------------------------------------
# Process isolation — the replacement for Celery's prefork time limits.
# ---------------------------------------------------------------------------

# Grace on top of the hard deadline: fork + the lazy games import in the
# child eat into wall time before the soft timer is armed.
_HARD_KILL_GRACE = 0.2

# Fork, not spawn: instant child start (spawn re-imports the interpreter)
# and the only start method the soft-timer arithmetic assumes. Works on
# Lambda and in the Linux containers; macOS defaults to spawn, so be
# explicit.
_mp = multiprocessing.get_context("fork")


def _soft_limit_handler(signum, frame):
    raise ExecutionTimeout()


def _child_main(conn, payload: Dict[str, Any]) -> None:
    """Forked child: own process group, armed soft timer, one run, one send.

    ``setsid`` makes the child a process-group leader so the parent's
    ``killpg`` reaps any descendants agent code forked (a plain SIGKILL on
    the child would leave fork-bomb grandchildren running).
    """
    os.setsid()
    signal.signal(signal.SIGALRM, _soft_limit_handler)
    signal.setitimer(signal.ITIMER_REAL, VALIDATION_TIMEOUT_SECONDS)
    envelope = run_validation(
        payload["code"], payload["game_name"], payload["team_name"]
    )
    signal.setitimer(signal.ITIMER_REAL, 0)
    # JSON string over the pipe: same round-trip the Celery broker applied,
    # so tuples and other JSON-lossy values arrive identically either way.
    conn.send(json.dumps(envelope))


def _kill_child(process) -> None:
    """SIGKILL the child's whole process group, then reap it."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass  # already exited (or died before setsid) — join reaps it
    process.join()


def run_validation_isolated(
    code: str, game_name: str, team_name: str
) -> Dict[str, Any]:
    """`run_validation` in a fresh child process under the 5s/6s limits.

    A child that dies without sending a result (hard kill, OOM, crash) maps
    to the canonical timeout envelope — the same collapse the old path made
    for TimeLimitExceeded/WorkerLostError.
    """
    payload = {"code": code, "game_name": game_name, "team_name": team_name}
    parent_conn, child_conn = _mp.Pipe(duplex=False)
    process = _mp.Process(target=_child_main, args=(child_conn, payload))
    process.start()
    child_conn.close()
    envelope: Optional[Dict[str, Any]] = None
    try:
        if parent_conn.poll(VALIDATION_TIME_LIMIT + _HARD_KILL_GRACE):
            envelope = json.loads(parent_conn.recv())
    except (EOFError, OSError, ValueError):
        envelope = None
    finally:
        _kill_child(process)
        parent_conn.close()
    if envelope is None:
        return timeout_validation_result()
    return envelope
