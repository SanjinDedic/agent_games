import functools
import logging
import os
import subprocess
import time
from datetime import datetime, timedelta
from typing import List, Optional, Union

import pytest
import pytz
from fastapi.testclient import TestClient
from sqlalchemy import inspect as sa_inspect, text
from sqlmodel import Session, SQLModel, create_engine, select

from backend.api import app
from backend.database.db_config import get_test_database_url
from backend.database.db_models import (
    Admin,
    DemoUser,
    League,
    Submission,
    Team,
    TeamType,
    get_password_hash,
)
from backend.database.db_session import get_db
from backend.routes.auth.auth_core import create_access_token

# Set environment variables for testing before any imports
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_tests")
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("USE_TEST_DB", "1")  # Signal to use the test database

os.environ["TESTING"] = "1"
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def run_docker_compose_command(
    command: List[str], timeout: int = 60
) -> subprocess.CompletedProcess:
    """Run a docker compose command with timeout"""
    try:
        full_command = ["docker", "compose"] + command
        logger.debug(f"Running docker compose command: {' '.join(full_command)}")

        result = subprocess.run(
            full_command, check=False, capture_output=True, text=True, timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        logger.error(f"Docker compose command timed out after {timeout} seconds")
        raise
    except Exception as e:
        logger.error(f"Error running docker compose command: {e}")
        raise


def ensure_postgres_test_running():
    """Ensure postgres_test container is running specifically"""
    try:
        # Check if postgres_test is already running and healthy
        result = run_docker_compose_command(["ps", "postgres_test", "--format", "json"])
        if "healthy" in result.stdout:
            logger.info("postgres_test is already running and healthy")
            return True

        # If not running or not healthy, ensure it's started with the test profile
        logger.info("Starting postgres_test container...")
        start_result = run_docker_compose_command(
            ["--profile", "test", "up", "-d", "postgres_test"]
        )

        if start_result.returncode != 0:
            logger.error(f"Failed to start postgres_test: {start_result.stderr}")
            return False

        # Wait for postgres_test to be healthy
        max_retries = 30
        for i in range(max_retries):
            result = run_docker_compose_command(
                ["ps", "postgres_test", "--format", "json"]
            )
            if "healthy" in result.stdout:
                logger.info("postgres_test is now healthy")
                return True
            logger.info(
                f"Waiting for postgres_test to be healthy... ({i+1}/{max_retries})"
            )
            time.sleep(2)

        logger.error("postgres_test failed to become healthy")
        return False
    except Exception as e:
        logger.error(f"Error ensuring postgres_test is running: {str(e)}")
        return False


def wait_for_services_simple(timeout: int = 120) -> bool:
    """
    Simple service waiting using Docker Compose's built-in capabilities
    """
    try:
        logger.info("Starting all test services and waiting for health checks...")

        # Use Docker Compose's --wait flag to wait for health checks
        result = run_docker_compose_command(
            ["--profile", "test", "up", "-d", "--wait"], timeout=timeout
        )

        if result.returncode == 0:
            logger.info("All services are healthy")
            return True
        else:
            logger.error(f"Services failed to start properly: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"Timed out waiting for services after {timeout} seconds")
        return False
    except Exception as e:
        logger.error(f"Error waiting for services: {e}")
        return False


@pytest.fixture(scope="session", autouse=True)
def docker_environment():
    """
    Primary fixture for Docker container management.
    Ensures containers are built (if needed) and running for the test session.
    """
    logger.info("Setting up Docker environment for test session")

    # Ensure postgres_test is running first
    if not ensure_postgres_test_running():
        pytest.fail("Failed to start postgres_test container")

    # Start all test services and wait for them to be healthy
    is_ready = wait_for_services_simple(timeout=180)

    if not is_ready:
        # Get service status for debugging
        try:
            ps_result = run_docker_compose_command(["ps"])
            logger.error(f"Service status:\n{ps_result.stdout}")
        except Exception:
            pass
        pytest.fail("Docker environment setup failed - services not healthy")

    logger.info("Docker environment ready for testing")

    yield

    logger.info("Test session complete - containers will remain running")


@pytest.fixture
def ensure_containers(request):
    """
    Fixture for tests that require containers.
    Verifies containers are healthy before each test.
    """
    test_name = request.node.name
    logger.info(f"Verifying containers for test: {test_name}")

    try:
        # Simple health check using docker compose ps
        result = run_docker_compose_command(
            ["ps", "--services", "--filter", "status=running"]
        )
        running_services = (
            result.stdout.strip().split("\n") if result.stdout.strip() else []
        )

        required_services = ["validator", "simulator", "postgres_test"]
        missing_services = [
            svc for svc in required_services if svc not in running_services
        ]

        if missing_services:
            logger.warning(f"Missing services for test {test_name}: {missing_services}")
            logger.info("Attempting to restart services...")

            # Try to restart services
            restart_result = run_docker_compose_command(
                ["--profile", "test", "up", "-d", "--wait"]
            )
            if restart_result.returncode != 0:
                logger.error(f"Failed to restart services: {restart_result.stderr}")
                pytest.fail("Could not restart services")

            logger.info("Services restarted successfully")

    except Exception as e:
        logger.error(f"Error checking container health: {e}")
        pytest.fail(f"Container health check failed for test {test_name}")

    logger.info(f"Services ready for test: {test_name}")
    return True


@pytest.fixture
def db_engine():
    """Create a new database engine for testing using the dedicated test database"""
    engine = create_engine(get_test_database_url())
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
    with Session(db_engine) as session:
        try:
            logger.debug(f"Test session using database: {db_engine.url}")
            yield session
            session.rollback()  # Roll back any uncommitted changes
        finally:
            session.close()  # Ensure session is closed


@pytest.fixture
def client(db_session) -> TestClient:
    """Create a test client with a test database session"""

    def get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = get_test_db
    return TestClient(app)


@pytest.fixture
def admin_token(db_session: Session) -> str:
    """Create an admin user and return an admin token"""
    admin = Admin(
        username="test_admin", password_hash=get_password_hash("test_password")
    )
    db_session.add(admin)
    db_session.commit()

    return create_access_token(
        data={"sub": "admin", "role": "admin"}, expires_delta=timedelta(minutes=30)
    )


@pytest.fixture
def team_token(db_session):
    """Create a test team with league assignment"""
    league = db_session.exec(select(League).where(League.name == "comp_test")).first()
    if not league:
        league = League(
            name="comp_test",
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=7),
            game="greedy_pig",
        )
        db_session.add(league)
        db_session.commit()
        db_session.refresh(league)

    team = Team(
        name="test_team",
        school_name="Test School",
        password_hash=get_password_hash("test_password"),
        league_id=league.id,
    )
    db_session.add(team)
    db_session.commit()

    return create_access_token(
        data={"sub": team.name, "role": "student"}, expires_delta=timedelta(minutes=30)
    )


@pytest.fixture
def auth_headers(admin_token) -> dict:
    """Return headers with admin authentication"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def team_auth_headers(team_token) -> dict:
    """Return headers with team authentication"""
    return {"Authorization": f"Bearer {team_token}"}


@pytest.fixture(autouse=True)
def setup_unassigned_league(db_session):
    """Create unassigned league if it doesn't exist"""
    unassigned = db_session.exec(
        select(League).where(League.name == "unassigned")
    ).first()

    if not unassigned:
        unassigned = League(
            name="unassigned",
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=7),
            game="greedy_pig",
        )
        db_session.add(unassigned)
        db_session.commit()

    return unassigned


@pytest.fixture
def test_league(db_session: Session) -> League:
    """Create a test league"""
    league = League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=1),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()
    return league


@pytest.fixture
def setup_demo_data(db_session: Session) -> None:
    """Set up demo data in the test database"""
    # Get unassigned league
    unassigned = db_session.exec(
        select(League).where(League.name == "unassigned")
    ).first()

    # Create demo teams and tracking records
    for i in range(2):
        # Check if team already exists
        team_name = f"demo_team_{i}"
        team = db_session.exec(select(Team).where(Team.name == team_name)).first()

        if not team:
            # Create the Team with is_demo flag
            team = Team(
                name=team_name + "_demo",
                school_name=team_name,
                password_hash="test_hash",
                league_id=unassigned.id,
                is_demo=True,  # Mark as demo
                team_type=TeamType.STUDENT,
            )
            db_session.add(team)
            db_session.commit()
            db_session.refresh(team)

            # Create separate DemoUser tracking record
            demo_user = DemoUser(
                username=team_name,  # This is the original username before adding "_Demo" suffix
                email=f"demo{i}@example.com",
                created_at=datetime.now(),
            )
            db_session.add(demo_user)
            db_session.commit()

            # Add submissions for each team
            for j in range(3):
                submission = Submission(
                    code=f"Demo code {j} for team {i}",
                    timestamp=datetime.now() - timedelta(minutes=j),
                    team_id=team.id,
                )
                db_session.add(submission)

    db_session.commit()


def inspect_db_state(tables: Union[List[str], str] = None, all_tables: bool = False):
    """
    Decorator to inspect and print database state before and after a test.

    Args:
        tables: List of table names to inspect, or a single table name
        all_tables: If True, inspect all tables regardless of tables parameter
    """

    def decorator(test_func):
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            # Get db_session from kwargs or pytest fixture
            session = None
            for arg in list(kwargs.values()) + list(args):
                if hasattr(arg, "execute") and hasattr(arg, "commit"):
                    session = arg
                    break

            if not session:
                print("WARNING: No database session found, cannot inspect db state")
                return test_func(*args, **kwargs)

            engine = session.get_bind()
            inspector = sa_inspect(engine)

            # Determine which tables to inspect
            table_names = []
            if all_tables:
                table_names = inspector.get_table_names()
            elif tables:
                if isinstance(tables, str):
                    table_names = [tables]
                else:
                    table_names = tables

            print(f"\n=== DATABASE STATE BEFORE TEST: {test_func.__name__} ===")
            for table_name in table_names:
                print(f"\n--- TABLE: {table_name} ---")
                try:
                    result = session.execute(
                        text(f"SELECT * FROM {table_name}")
                    ).fetchall()
                    if result:
                        # Get column names
                        columns = [
                            col["name"] for col in inspector.get_columns(table_name)
                        ]
                        print(f"Columns: {columns}")
                        print(f"Row count: {len(result)}")
                        # Print first 5 rows for preview
                        for i, row in enumerate(result[:5]):
                            print(f"Row {i+1}: {row}")
                        if len(result) > 5:
                            print(f"... and {len(result) - 5} more rows")
                    else:
                        print("Table is empty")
                except Exception as e:
                    print(f"Error inspecting table {table_name}: {e}")

            # Run the test
            result = test_func(*args, **kwargs)

            print(f"\n=== DATABASE STATE AFTER TEST: {test_func.__name__} ===")
            for table_name in table_names:
                print(f"\n--- TABLE: {table_name} ---")
                try:
                    result_after = session.execute(
                        text(f"SELECT * FROM {table_name}")
                    ).fetchall()
                    if result_after:
                        columns = [
                            col["name"] for col in inspector.get_columns(table_name)
                        ]
                        print(f"Columns: {columns}")
                        print(f"Row count: {len(result_after)}")
                        for i, row in enumerate(result_after[:5]):
                            print(f"Row {i+1}: {row}")
                        if len(result_after) > 5:
                            print(f"... and {len(result_after) - 5} more rows")
                    else:
                        print("Table is empty")
                except Exception as e:
                    print(f"Error inspecting table {table_name}: {e}")

            return result

        return wrapper

    return decorator


def print_db_state(session, tables=None, all_tables=False, label=""):
    """
    Function to inspect and print database state at any point in the code.

    Args:
        session: SQLAlchemy session
        tables: List of table names to inspect, or a single table name
        all_tables: If True, inspect all tables regardless of tables parameter
        label: Optional label to include in the output
    """
    engine = session.get_bind()
    inspector = sa_inspect(engine)

    # Determine which tables to inspect
    table_names = []
    if all_tables:
        table_names = inspector.get_table_names()
    elif tables:
        if isinstance(tables, str):
            table_names = [tables]
        else:
            table_names = tables

    print(f"\n=== DATABASE STATE {label} ===")
    for table_name in table_names:
        print(f"\n--- TABLE: {table_name} ---")
        try:
            result = session.execute(text(f"SELECT * FROM {table_name}")).fetchall()
            if result:
                columns = [col["name"] for col in inspector.get_columns(table_name)]
                print(f"Columns: {columns}")
                print(f"Row count: {len(result)}")
                for i, row in enumerate(result[:5]):
                    print(f"Row {i+1}: {row}")
                if len(result) > 5:
                    print(f"... and {len(result) - 5} more rows")
            else:
                print("Table is empty")
        except Exception as e:
            print(f"Error inspecting table {table_name}: {e}")
