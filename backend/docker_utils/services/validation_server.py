import ast
import asyncio
import logging
import multiprocessing as mp
import os
import time
import traceback as tb
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Union

from fastapi import FastAPI
from pydantic import BaseModel

from backend.database.db_models import League
from backend.games.game_factory import GameFactory

# Configure logging to use console only
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Only use StreamHandler for console output
)

logger = logging.getLogger(__name__)

app = FastAPI()

# Universal hard cap for agent validation (single game + simulations).
VALIDATION_TIMEOUT_SECONDS = 5

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


class ValidationRequest(BaseModel):
    code: str
    game_name: str
    team_name: str
    num_simulations: int = 100
    custom_rewards: Optional[list] = None


class ValidationResponse(BaseModel):
    status: str
    message: Optional[str] = None
    feedback: Union[str, Dict, None] = None
    simulation_results: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    # Full Python traceback for a runtime error, and anything the agent/game
    # printed. Captured inside the worker process; rendered by the hint builder.
    traceback: Optional[str] = None
    stdout: Optional[str] = None


# --- Process-isolated execution --------------------------------------------
# Run each agent in a forked child instead of a thread. The container is Linux,
# so `fork` is available: the child inherits the already-imported game framework
# (GameFactory, SQLModel, ...) via copy-on-write, so there is no per-request
# re-import cost. Wins over the thread path:
#   * true parallelism (no GIL) across cores for the CPU-bound sims,
#   * a real timeout — terminate() actually kills a runaway agent (a thread
#     cannot be killed; asyncio.timeout leaks the still-running thread),
#   * the process boundary is a single catch-all: stderr/traceback + stdout
#     are captured for every game without per-game try/except.
_MP_CTX = mp.get_context("fork")
# Bound concurrent children: leave headroom for uvicorn + stay under pids_limit.
_MAX_PROCS = max(1, min(8, (os.cpu_count() or 2)))
_proc_sem: Optional[asyncio.Semaphore] = None


def _get_proc_sem() -> asyncio.Semaphore:
    """Lazily create the semaphore on the running loop."""
    global _proc_sem
    if _proc_sem is None:
        _proc_sem = asyncio.Semaphore(_MAX_PROCS)
    return _proc_sem


def _child_run(conn, game_name, code, team_name, num_simulations, custom_rewards):
    """Child entrypoint: run the full validation load and pipe back a dict.

    Logging is disabled at the top to avoid a deadlock if the parent held the
    logging lock at fork time, and to keep the (inherited) handlers quiet.
    """
    import contextlib
    import io
    import logging as _logging

    _logging.disable(_logging.CRITICAL)
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
    except Exception as e:  # noqa: BLE001 - the process boundary is the catch-all
        result = {
            "status": "error",
            "message": f"Error during simulation: {str(e)}",
            "traceback": tb.format_exc(),
        }
    captured = buf.getvalue()
    if captured.strip():
        result["stdout"] = captured
    try:
        conn.send(result)
    finally:
        conn.close()


def _supervise(game_name, code, team_name, num_simulations, custom_rewards) -> Dict[str, Any]:
    """Run one validation in a child process; enforce the timeout with a kill."""
    parent_conn, child_conn = _MP_CTX.Pipe()
    proc = _MP_CTX.Process(
        target=_child_run,
        args=(child_conn, game_name, code, team_name, num_simulations, custom_rewards),
    )
    proc.start()
    child_conn.close()  # only the child writes
    try:
        if parent_conn.poll(VALIDATION_TIMEOUT_SECONDS):
            try:
                result = parent_conn.recv()
            except EOFError:
                result = {
                    "status": "error",
                    "message": "Validation crashed before returning a result.",
                }
            proc.join(timeout=1)
            if proc.is_alive():
                proc.terminate()
                proc.join()
            return result
        # Timed out: kill the runaway child.
        proc.terminate()
        proc.join()
        return {
            "status": "error",
            "message": (
                f"Your agent consumes too much time - validation did not "
                f"finish within {VALIDATION_TIMEOUT_SECONDS} seconds. "
                f"The agent may be too slow or stuck in a loop."
            ),
        }
    finally:
        parent_conn.close()


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


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/validate", response_model=ValidationResponse)
async def validate_submission(request: ValidationRequest) -> ValidationResponse:
    """Validate submitted code and run test simulation"""
    logger.info(f"Received validation request for team {request.team_name}")
    try:
        # Code safety check stays in the parent: cheap, no need to fork for it.
        is_safe, error_message = validate_code(request.code)
        if not is_safe:
            return ValidationResponse(
                status="error", message=f"Agent code is not safe: {error_message}"
            )

        # Everything that runs the agent happens in a forked child. The blocking
        # supervise() waits on the child via one helper thread so the event loop
        # stays free; the semaphore bounds how many children run at once.
        async with _get_proc_sem():
            result = await asyncio.to_thread(
                _supervise,
                request.game_name,
                request.code,
                request.team_name,
                request.num_simulations,
                request.custom_rewards,
            )

        return ValidationResponse(
            status=result.get("status", "error"),
            message=result.get("message"),
            feedback=result.get("feedback"),
            simulation_results=result.get("simulation_results"),
            duration_ms=result.get("duration_ms"),
            traceback=result.get("traceback"),
            stdout=result.get("stdout"),
        )

    except Exception as e:
        logger.error(f"Unexpected error during validation: {str(e)}")
        return ValidationResponse(
            status="error", message=f"Unexpected error during validation: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
