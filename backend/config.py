import os

from dotenv import load_dotenv


def find_project_root(current_dir=os.path.dirname(os.path.abspath(__file__))):
    """
    Find the project root directory by looking for key project files/directories.
    Returns absolute path to project root.
    """
    # Markers that indicate we're in the right directory
    project_markers = {
        "directories": ["games", "routes", "docker_utils", "database"],
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

# Load environment variables
load_dotenv()

CURRENT_DB = os.path.join(ROOT_DIR, "teams.db")
GUEST_LEAGUE_EXPIRY = 24  # hours
ADMIN_LEAGUE_EXPIRY = 180  # 1 week and 12 hours
GAMES = ["greedy_pig", "prisoners_dilemma", "lineup4"]

# Service URLs configured for Docker Compose services by default
# These work the same in both local and server environments
VALIDATOR_URL = os.getenv("VALIDATOR_URL", "http://validator:8001")
SIMULATOR_URL = os.getenv("SIMULATOR_URL", "http://simulator:8002")
API_URL = os.getenv("API_URL", "http://api:8000")

# This is kept for backwards compatibility
DOCKER_API_URL = API_URL

DEMO_TOKEN_EXPIRY = 60  # minutes

# Set a default SECRET_KEY for tests if not available in environment
# In production, this should always be overridden by the actual secret key
# from environment vars
SECRET_KEY = os.getenv("SECRET_KEY", "test_secret_key_for_development_only")

# Import after defining constants to avoid circular import
from backend.routes.auth.auth_config import create_service_token

# Generate a service token with the SECRET_KEY (which may be the fallback for tests)
SERVICE_TOKEN = create_service_token()
