import os
from dotenv import load_dotenv

# Load environment variables from root .env file
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
load_dotenv(os.path.join(project_root, ".env"))

def get_database_url():
    """
    Get the database URL from environment variable.
    Handles Docker vs local execution automatically.
    Modifies database name based on DB_ENVIRONMENT.
    """
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    # Check if we're in test environment and modify database name and port/host
    db_environment = os.environ.get("DB_ENVIRONMENT")
    if db_environment == "test":
        # Replace database name with test database
        if "/agent_games" in database_url:
            database_url = database_url.replace("/agent_games", "/agent_games_test")

        # For test environment, handle both Docker and local execution
        if os.path.exists("/.dockerenv"):
            # Running inside Docker, use postgres_test service name
            if "@postgres:" in database_url:
                database_url = database_url.replace("@postgres:", "@postgres_test:")
        else:
            # Running outside Docker, use localhost:5433 for postgres_test
            database_url = database_url.replace(":5432", ":5433")

    # Check if we're running outside Docker but DATABASE_URL points to Docker service
    if not os.path.exists("/.dockerenv") and "@postgres:" in database_url:
        # Replace Docker service name with localhost for local execution
        database_url = database_url.replace("@postgres:", "@localhost:")

    # Ensure we're using psycopg3 driver
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://")

    return database_url

# Function removed - use get_database_url() with DB_ENVIRONMENT=test instead
