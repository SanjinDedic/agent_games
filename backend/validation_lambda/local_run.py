"""Local subprocess entry point: one JSON event on stdin, one envelope out.

Run as ``python -m backend.validation_lambda.local_run`` by the API client
when VALIDATION_LAMBDA_FUNCTION is unset (dev, CI, emergency prod fallback).
A fresh interpreter with a scrubbed environment — not a fork of the API
process — so agent code never inherits secrets, DB sockets, or the API
heap. Inside, the same fork/soft-timer/hard-kill machinery as the Lambda
runs (handler → run_validation_isolated).

Before anything imports the games tree, a stdlib-only stub is installed for
``backend.config``: the real module runs ``load_dotenv`` on ``.env`` AND
``backend/routes/payments/.env`` at import time, which would re-inject the
exact secrets ``_scrubbed_env()`` scrubbed into the process that execs agent
code. The stub carries only what the games need (ROOT_DIR, GAMES) — the same
substitution the browser worker makes (validation.worker.js) and the same
one deploy.sh bakes into the Lambda zip as a generated config.py. This stub
lives here, in the dedicated subprocess entry point, and must never move
into a module the API or the tests import: it would poison the real
``backend.config`` for the whole process.

The result is written to a dup of the original stdout taken before fd 1 is
pointed at /dev/null, so agent code that writes to fd 1 directly (bypassing
sys.stdout redirection) cannot corrupt the JSON the API client parses.
"""

import json
import os
import sys
import types


def _install_config_stub() -> None:
    """Register a stdlib backend.config stand-in before the games import it.

    Discovery mirrors backend/config.py::_discover_games: a folder counts as
    a game when it holds player.py, <name>.py, validation_players.py.
    """
    if "backend.config" in sys.modules:
        return
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    games_dir = os.path.join(backend_dir, "games")
    games = []
    for entry in sorted(os.listdir(games_dir)):
        game_dir = os.path.join(games_dir, entry)
        if not os.path.isdir(game_dir):
            continue
        if entry.startswith("_") or entry.startswith("."):
            continue
        required = ["player.py", f"{entry}.py", "validation_players.py"]
        if all(os.path.isfile(os.path.join(game_dir, f)) for f in required):
            games.append(entry)
    stub = types.ModuleType("backend.config")
    stub.ROOT_DIR = backend_dir
    stub.GAMES = games
    sys.modules["backend.config"] = stub


_install_config_stub()

from backend.validation_lambda.handler import handle  # noqa: E402


def main() -> None:
    event = json.loads(sys.stdin.read())
    result_fd = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    os.close(devnull)
    envelope = handle(event)
    os.write(result_fd, json.dumps(envelope).encode())
    os.close(result_fd)


if __name__ == "__main__":
    main()
