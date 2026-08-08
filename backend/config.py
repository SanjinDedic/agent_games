import os

def find_project_root(current_dir=os.path.dirname(os.path.abspath(__file__))):
    """
    Find the project root directory by looking for key project files/directories.
    Returns absolute path to project root.
    """
    # Markers that indicate we're in the right directory
    project_markers = {
        "directories": ["games", "routes", "database"],
        "files": ["api.py", "config.py"],
    }

    # Check if current directory has the markers we're looking for
    current_items = os.listdir(current_dir)
    has_markers = all(
        d in current_items for d in project_markers["directories"]
    ) and all(f in current_items for f in project_markers["files"])

    if has_markers:
        return current_dir

    # If we hit root directory or go too far up, raise error
    parent = os.path.dirname(current_dir)
    if parent == current_dir:
        raise RuntimeError("Could not find project root directory")

    # Recursively check parent directory
    return find_project_root(parent)


# Set the root directory
ROOT_DIR = find_project_root()
PROJECT_ROOT = os.path.dirname(ROOT_DIR)  # Get the parent directory of backend folder

# Load environment variables
from dotenv import load_dotenv

# Load .env from project root (public, non-secret dev defaults)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

CURRENT_DB = os.path.join(ROOT_DIR, "teams.db")
GUEST_LEAGUE_EXPIRY = 24  # hours
ADMIN_LEAGUE_EXPIRY = 180  # 1 week and 12 hours


def _discover_games(games_dir):
    """Scan backend/games/ for valid game folders.

    A folder counts as a game when it contains all three required files:
    player.py, <folder_name>.py, validation_players.py.
    """
    if not os.path.isdir(games_dir):
        return []
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
    return games


GAMES = _discover_games(os.path.join(ROOT_DIR, "games"))


# Set a default SECRET_KEY for tests if not available in environment
# In production, this should always be overridden by the actual secret key
# from environment vars
SECRET_KEY = os.getenv("SECRET_KEY", "test_secret_key_for_tests")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BENCHMARK_TOKEN = os.getenv("BENCHMARK_TOKEN")


# One deployment serves one audience, so the classroom-vs-competition wording is
# deploy configuration rather than per-account state. The frontend reads these
# from GET /config and swaps its nouns via AgentGames/Shared/terminology.js;
# API paths, JSON keys and route names always keep the league/team names.
# Defaults to competition because that is the wording the app rendered before
# the mode existed; a classroom deployment opts in explicitly.
SITE_MODES = ("classroom", "competition")
SITE_MODE = os.getenv("SITE_MODE", "competition").strip().lower()
if SITE_MODE not in SITE_MODES:
    # Fail at import rather than silently render the wrong nouns to a class of
    # students for a term.
    raise RuntimeError(
        f"SITE_MODE must be one of {', '.join(SITE_MODES)} (got {SITE_MODE!r})"
    )

SITE_NAME = os.getenv("SITE_NAME", "Agent Games").strip()
SITE_ICON = os.getenv("SITE_ICON", "").strip() or None
