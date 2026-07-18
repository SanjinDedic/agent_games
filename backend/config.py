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

# Load payment secrets from a gitignored, per-developer file. Available inside
# the api container via the ./backend volume mount. Does not override values
# already set in the environment.
load_dotenv(os.path.join(ROOT_DIR, "routes", "payments", ".env"))

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

# Stripe (test mode). Keys/prices come from .env; webhook secret comes from
# the Stripe CLI `stripe listen` output during local development.
STRIPE_SECRET_KEY = os.getenv("SECRET_STRIPE_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
# Two Prices per tier: a one-time 90-day pass (Checkout mode="payment") and a
# yearly recurring subscription (mode="subscription"). The buyer's auto-renew
# choice selects which one is used. The annual Price is higher than the 90-day
# one (e.g. club: $99 once vs $299/yr; university: $299 once vs $599/yr).
STRIPE_PRICE_CLUB_ONCE = os.getenv("STRIPE_PRICE_CLUB_ONCE")
STRIPE_PRICE_CLUB_YEAR = os.getenv("STRIPE_PRICE_CLUB_YEAR")
STRIPE_PRICE_UNI_ONCE = os.getenv("STRIPE_PRICE_UNI_ONCE")
STRIPE_PRICE_UNI_YEAR = os.getenv("STRIPE_PRICE_UNI_YEAR")
# Teacher plan: 90-day pass only, no annual option. The whole-school teacher
# tier reuses STRIPE_PRICE_UNI_ONCE (same $299 / 500-student product).
STRIPE_PRICE_TEACHER_ONCE = os.getenv("STRIPE_PRICE_TEACHER_ONCE")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BENCHMARK_TOKEN = os.getenv("BENCHMARK_TOKEN")
