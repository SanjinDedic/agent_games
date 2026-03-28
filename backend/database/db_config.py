import os
from dotenv import load_dotenv

# Load environment variables from root .env file
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
load_dotenv(os.path.join(project_root, ".env"))

def get_database_url():
    """
    Get the database URL based on environment.
    Uses hardcoded test URLs for testing, production URL from env otherwise.
    """
    db_environment = os.environ.get("DB_ENVIRONMENT")

    if db_environment == "test":
        # Test database on same Postgres cluster, different database name
        if os.path.exists("/.dockerenv"):
            return "postgresql+psycopg://postgres:local_pw@postgres:5432/agent_games_test"
        else:
            return "postgresql+psycopg://postgres:local_pw@localhost:5432/agent_games_test"

    # Production environment - use environment variable
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:local_pw@postgres:5432/agent_games",
    )
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required for production")

    # Handle Docker vs local for production
    if not os.path.exists("/.dockerenv") and "@postgres:" in database_url:
        # Running outside Docker, replace service name with localhost
        database_url = database_url.replace("@postgres:", "@localhost:")

    # Ensure we're using psycopg3 driver
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://")

    return database_url
