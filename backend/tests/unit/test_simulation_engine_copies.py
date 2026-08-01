"""The browser simulation runner ships VERBATIM copies of the game engine.

frontend/src/pyodide/games/engine/ mirrors backend/games/ file-for-file; the
simulation worker writes the copies onto Pyodide's filesystem so the engine
behaves identically in the browser and on the server. Unlike the exercise
harness (a semantic extraction), these files are meant to be byte-identical —
so the contract is plain byte equality. Edit the backend original and
re-copy; never edit a copy directly.

The frontend files reach the test container through the same read-only
volume as the exercise harness (docker-compose.yml).
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
ENGINE_DIR = REPO_ROOT / "frontend" / "src" / "pyodide" / "games" / "engine"
BACKEND_GAMES = REPO_ROOT / "backend" / "games"

# One row per shipped engine file: (copy under engine/, original under
# backend/games/). Extend when porting another game to the browser runner.
ENGINE_COPIES = [
    ("base_game.py", "base_game.py"),
    ("game_factory.py", "game_factory.py"),
    ("greedy_pig/greedy_pig.py", "greedy_pig/greedy_pig.py"),
    ("greedy_pig/player.py", "greedy_pig/player.py"),
    ("greedy_pig/validation_players.py", "greedy_pig/validation_players.py"),
]


@pytest.mark.parametrize("copy_rel, original_rel", ENGINE_COPIES)
def test_engine_copy_matches_backend_original(copy_rel, original_rel):
    copy_path = ENGINE_DIR / copy_rel
    original_path = BACKEND_GAMES / original_rel
    assert copy_path.is_file(), f"missing engine copy: {copy_path}"
    assert copy_path.read_bytes() == original_path.read_bytes(), (
        f"{copy_path} has drifted from {original_path} — re-copy the backend "
        f"original (cp {original_path} {copy_path})"
    )
