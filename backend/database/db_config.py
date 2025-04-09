import os
from dotenv import load_dotenv

# Load environment variables from root .env file
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
load_dotenv(os.path.join(project_root, ".env"))

# Get database configuration from environment variables with fallbacks
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get(
    "POSTGRES_PASSWORD", ""
)  # Password should be in .env file
DB_NAME = os.environ.get("DB_NAME", "agent_games")
TEST_DB_NAME = os.environ.get("TEST_DB_NAME", "agent_games_test")

def get_database_url():
    """
    Get the database URL from environment variable or use environment variables.
    This works both for Docker and local setups, assuming the Docker PostgreSQL service is also
    accessible on localhost:5432.
    """
    # First check for explicit DATABASE_URL environment variable (highest priority)
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        # Check if we're running tests from outside Docker but using Docker services
        if os.environ.get("TESTING") == "1" and not os.path.exists("/.dockerenv"):
            # Replace postgres service name with localhost
            if "@postgres:" in database_url:
                database_url = database_url.replace("@postgres:", "@localhost:")

        # Make sure we're using psycopg3 by specifying the dialect+driver
        if database_url.startswith("postgresql://"):
            return database_url.replace("postgresql://", "postgresql+psycopg://")
        return database_url

    # Check if we're running tests and outside Docker
    if os.environ.get("TESTING") == "1" and not os.path.exists("/.dockerenv"):
        # For tests, use the dedicated test database
        if os.environ.get("USE_TEST_DB") == "1":
            return get_test_database_url()
        # Use localhost instead of service name for tests running outside Docker
        return f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5432/{DB_NAME}"

    # Default PostgreSQL URL using psycopg3 driver and service name for Docker environment
    return f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres:5432/{DB_NAME}"


def get_test_database_url():
    """
    Get the database URL for the test database.
    This is a dedicated PostgreSQL instance running on port 5433.
    """
    # Check if we're running inside Docker
    if os.path.exists("/.dockerenv"):
        # When running inside Docker, use the service name
        return f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres_test:5432/{TEST_DB_NAME}"
    else:
        # When running outside Docker, access via localhost
        return f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5433/{TEST_DB_NAME}"
