import os

from dotenv import load_dotenv


# Get path to the directory containing config.py, then go up directories until we hit the right level
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

# Other config variables
SECRET_KEY = os.getenv("SECRET_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
CURRENT_DB = os.path.join(ROOT_DIR, "teams.db")
GUEST_LEAGUE_EXPIRY = 24  # hours
ADMIN_LEAGUE_EXPIRY = 180  # 1 week and 12 hours
GAMES = ["greedy_pig", "prisoners_dilemma"]


def get_database_url():
    if os.environ.get("TESTING") == "1":
        test_db_path = os.path.join(ROOT_DIR, "test.db")
        return f"sqlite:///{test_db_path}"
    else:
        teams_db_path = os.path.join(ROOT_DIR, "teams.db")
        return f"sqlite:///{teams_db_path}"


if __name__ == "__main__":
    print(f"Project root directory: {ROOT_DIR}")
    print(f"Database URL: {get_database_url()}")
