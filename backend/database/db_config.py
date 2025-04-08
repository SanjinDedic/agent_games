import os


def get_database_url():
    """
    Get the database URL from environment variable or use default PostgreSQL connection.
    This works both for Docker and local setups, assuming the Docker PostgreSQL service is also
    accessible on localhost:5432.
    """
    # First check for environment variable (set in docker-compose)
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
        return (
            "postgresql+psycopg://postgres:postgrespassword@localhost:5432/agent_games"
        )

    # Default PostgreSQL URL using psycopg3 driver and service name for Docker environment
    return "postgresql+psycopg://postgres:postgrespassword@postgres:5432/agent_games"


def get_test_database_url():
    """
    Get the database URL for the test database.
    This is a dedicated PostgreSQL instance running on port 5433.
    """
    # Check if we're running inside Docker
    if os.path.exists("/.dockerenv"):
        # When running inside Docker, use the service name
        return "postgresql+psycopg://postgres:postgrespassword@postgres_test:5432/agent_games_test"
    else:
        # When running outside Docker, access via localhost
        return "postgresql+psycopg://postgres:postgrespassword@localhost:5433/agent_games_test"
