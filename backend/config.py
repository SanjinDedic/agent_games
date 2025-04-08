import os

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
PROJECT_ROOT = os.path.dirname(ROOT_DIR)  # Get the parent directory of backend folder

# Load environment variables
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

CURRENT_DB = os.path.join(ROOT_DIR, "teams.db")
GUEST_LEAGUE_EXPIRY = 24  # hours
ADMIN_LEAGUE_EXPIRY = 180  # 1 week and 12 hours
GAMES = ["greedy_pig", "prisoners_dilemma", "lineup4"]


# Service URL configuration
def get_service_url(service_name, endpoint=None):
    """
    Get environment-aware URL for a service

    Args:
        service_name: Name of the service ('validator', 'simulator', 'api')
        endpoint: Optional endpoint to append (without leading slash)

    Returns:
        Full URL to the service, using localhost in test environment
        and service name in production
    """
    port_mapping = {"validator": 8001, "simulator": 8002, "api": 8000}

    if service_name not in port_mapping:
        raise ValueError(f"Unknown service: {service_name}")

    port = port_mapping[service_name]

    # Use localhost for tests, service name for production
    host = "localhost" if os.environ.get("TESTING") == "1" else service_name

    base_url = f"http://{host}:{port}"

    # Append endpoint if provided
    if endpoint:
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        return f"{base_url}{endpoint}"

    return base_url


# Define service URLs using the helper function
VALIDATOR_URL = get_service_url("validator")
SIMULATOR_URL = get_service_url("simulator")
API_URL = get_service_url("api")

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
