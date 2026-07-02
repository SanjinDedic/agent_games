"""Agent code validation: AST safety check + the Celery validation task.

The AST check (validate_code) runs in the API process before enqueue — unsafe
code never reaches a worker. The run_validation task executes the agent inside
a worker child process; worker_max_tasks_per_child=1 gives every task a fresh
process, so a monkeypatching or crashing agent cannot contaminate later runs.

The error message strings here are prefix-matched by
backend/routes/ai/hint_context.py (classify_outcome) — do not reword them.
"""

import ast
import contextlib
import io
import time
import traceback as tb
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from celery.exceptions import SoftTimeLimitExceeded

from backend.celery_app import celery_app
from backend.database.db_models import League
from backend.games.game_factory import GameFactory

# Universal hard cap for agent validation (single game + simulations).
VALIDATION_TIMEOUT_SECONDS = 5

# Prefix-matched by hint_context.classify_outcome — do not reword. Shared by
# the task's soft-limit handler and the routers' hard-kill fallback.
TIMEOUT_MESSAGE = (
    f"Your agent consumes too much time - validation did not "
    f"finish within {VALIDATION_TIMEOUT_SECONDS} seconds. "
    f"The agent may be too slow or stuck in a loop."
)

# Security configuration
ALLOWED_MODULES = {
    "random": None,
    "string": None,
    "math": None,
    "games": None,
    "player": None,
}

RISKY_FUNCTIONS = [
    "eval",
    "exec",
    "open",
    "compile",
    "execfile",
    "input",
    "os",
    "sys",
    "subprocess",
    "importlib",
    "__import__",
]


class CodeValidator(ast.NodeVisitor):
    """AST visitor for validating code safety"""

    def __init__(self):
        self.safe = True
        self.error_message = None

    def visit_Import(self, node):
        for alias in node.names:
            if not self._is_allowed_import(alias.name):
                self.safe = False
                self.error_message = f"Unauthorized import: {alias.name}"
                return
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if not self._is_allowed_import(node.module, node.names[0].name):
            self.safe = False
            self.error_message = (
                f"Unauthorized import: {node.module}.{node.names[0].name}"
            )
            return
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in RISKY_FUNCTIONS:
            self.safe = False
            self.error_message = f"Unauthorized function call: {node.func.id}"
            return
        self.generic_visit(node)

    def _is_allowed_import(self, module: str, submodule: str = None) -> bool:
        parts = module.split(".")
        current = ALLOWED_MODULES
        for part in parts:
            if part not in current:
                return False
            if current[part] is None:
                return True
            current = current[part]
        return submodule in current if submodule else True


def validate_code(code: str) -> Tuple[bool, Optional[str]]:
    """Validate code safety using AST analysis"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error in code: {str(e)}"

    validator = CodeValidator()
    validator.visit(tree)
    return validator.safe, validator.error_message


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


@celery_app.task(
    name="validation.run",
    soft_time_limit=VALIDATION_TIMEOUT_SECONDS,
    # Hard SIGKILL backstop: SoftTimeLimitExceeded is a plain Exception, so an
    # agent with a bare `except Exception` inside its loop can swallow it.
    time_limit=8,
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
