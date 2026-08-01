"""The browser Pyodide workers ship VERBATIM copies of the game engine.

frontend/src/pyodide/games/engine/ mirrors backend/games/ file-for-file; the
simulation and validation workers write the copies onto Pyodide's filesystem
so the engine behaves identically in the browser and on the server. Unlike
the exercise harness (a semantic extraction), these files are meant to be
byte-identical — so the contract is plain byte equality. Edit the backend
original and re-copy; never edit a copy directly.

Every discovered game must be shipped: agent validation runs in-browser for
all games, so a new game folder under backend/games/ fails here until its
three engine files are copied and listed in GAME_NAMES (and registered in
frontend/src/pyodide/games/index.js).

The frontend files reach the test container through the same read-only
volume as the exercise harness (docker-compose.yml).
"""

from pathlib import Path

import pytest

from backend.config import GAMES

REPO_ROOT = Path(__file__).resolve().parents[3]
ENGINE_DIR = REPO_ROOT / "frontend" / "src" / "pyodide" / "games" / "engine"
BACKEND_GAMES = REPO_ROOT / "backend" / "games"

SHARED_FILES = ["base_game.py", "game_factory.py"]

# Every game shipped to the browser: three engine files each, at the same
# relative path on both sides. Extend when adding a game.
GAME_NAMES = [
    "arena_champions",
    "breakthrough",
    "greedy_pig",
    "hearts",
    "lineup4",
    "ohhell",
    "prisoners_dilemma",
    "thirteen",
]

ENGINE_COPIES = SHARED_FILES + [
    f"{game}/{filename}"
    for game in GAME_NAMES
    for filename in (f"{game}.py", "player.py", "validation_players.py")
]


def test_every_discovered_game_is_shipped():
    assert sorted(GAME_NAMES) == sorted(GAMES), (
        "backend/games/ and the shipped engine list have diverged — copy the "
        "new game's engine files, register it in "
        "frontend/src/pyodide/games/index.js, and add it to GAME_NAMES here"
    )


@pytest.mark.parametrize("rel_path", ENGINE_COPIES)
def test_engine_copy_matches_backend_original(rel_path):
    copy_path = ENGINE_DIR / rel_path
    original_path = BACKEND_GAMES / rel_path
    assert copy_path.is_file(), f"missing engine copy: {copy_path}"
    assert copy_path.read_bytes() == original_path.read_bytes(), (
        f"{copy_path} has drifted from {original_path} — re-copy the backend "
        f"original (cp {original_path} {copy_path})"
    )
