import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
#root directory of the project absolute path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_DB = os.path.join(ROOT_DIR, "teams.db")
GUEST_LEAGUE_EXPIRY = 24 #hours
ADMIN_LEAGUE_EXPIRY = 180 #1 week and 12 hours
GAMES = ["greedy_pig", "prisoners_dilemma"]

def get_database_url():
    if os.environ.get("TESTING") == "1":
        test_db_path = os.path.join(ROOT_DIR, "test.db")  # Use a relative path for the test database
        return f"sqlite:///{test_db_path}"
    else:
        teams_db_path = os.path.join(ROOT_DIR, "teams.db")  # Use a relative path for the production database
        return f"sqlite:///{teams_db_path}"