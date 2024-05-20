import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
CURRENT_DIR = os.path.dirname(__file__)
CURRENT_DB = os.path.join(CURRENT_DIR, "teams.db")
GUEST_LEAGUE_EXPIRY = 24 #hours
ADMIN_LEAGUE_EXPIRY = 180 #1 week and 12 hours

def get_database_url():
    if os.environ.get("TESTING"):
        test_db_path = os.path.join(CURRENT_DIR, "test.db")  # Use a relative path for the test database
        return f"sqlite:///{test_db_path}"
        #Try an in memory db
        #return "sqlite:///:memory:"
    else:
        return f"sqlite:///{CURRENT_DB}"