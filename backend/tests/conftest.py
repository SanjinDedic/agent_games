import functools
import logging
import os
import subprocess
import time
from datetime import datetime, timedelta
from typing import List, Union

import pytest
import pytz
from fastapi.testclient import TestClient
from sqlalchemy import inspect as sa_inspect, text
from sqlmodel import Session, SQLModel, create_engine, select

from backend.api import app
from backend.database.db_config import get_database_url
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
os.environ["DB_ENVIRONMENT"] = "test"
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

        # Set environment variables for test mode
        env = os.environ.copy()
        env["DB_ENVIRONMENT"] = "test"

        result = subprocess.run(
            full_command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return result
    except subprocess.TimeoutExpired:
        logger.error(f"Docker compose command timed out after {timeout} seconds")
        raise
    except Exception as e:
        logger.error(f"Error running docker compose command: {e}")
        raise


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up complete test environment with proper database switching
    """
    # Set test environment FIRST
    os.environ["DB_ENVIRONMENT"] = "test"

    # Print database info
    database_url = get_database_url()
    print(f"\n{'='*60}")
    print(f"TEST SUITE STARTING")
    print(f"Database URL: {database_url}")
    print(f"{'='*60}\n")

    # Stop any running services
    logger.info("Stopping any running services...")
    try:
        run_docker_compose_command(["--profile", "test", "down"])
        run_docker_compose_command(["--profile", "dev", "down"])
    except Exception as e:
        logger.warning(f"Error stopping services: {e}")

    # Start test services with test profile
    logger.info("Starting test services...")
    try:
        result = run_docker_compose_command(
            ["--profile", "test", "up", "-d", "--wait"], timeout=120
        )
        if result.returncode == 0:
            logger.info("All test services are healthy")
        else:
            logger.error(f"Services failed to start: {result.stderr}")
            pytest.fail("Docker environment setup failed")
    except Exception as e:
        logger.error(f"Error setting up test environment: {e}")
        pytest.fail("Docker environment setup failed")

    yield
    logger.info("Test session complete")


@pytest.fixture
def ensure_containers(request):
    """
    Verify that all 4 required services are healthy before each test.
    Required services: api, validator, simulator, postgres_test
    """
    test_name = request.node.name
    logger.info(f"Verifying containers for test: {test_name}")

    try:
        # Check that all required services are running
        result = run_docker_compose_command(
            ["ps", "--services", "--filter", "status=running"]
        )
        running_services = (
            result.stdout.strip().split("\n") if result.stdout.strip() else []
        )

        required_services = ["api", "validator", "simulator", "postgres_test"]
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

    logger.info(f"All services ready for test: {test_name}")
    return True


@pytest.fixture
def db_engine():
    """Create database engine for testing using the dedicated test database"""
    database_url = get_database_url()
    logger.info(f"Creating database engine: {database_url}")

    # Create the test database if it doesn't exist
    try:
        engine = create_engine(database_url)
        with engine.connect():
            pass  # Test connection
        logger.info("Test database already exists")
    except Exception as e:
        logger.info(f"Test database doesn't exist, creating it: {e}")
        # Connect to postgres to create the test database
        base_url = database_url.rsplit("/", 1)[0] + "/postgres"
        admin_engine = create_engine(base_url)

        # Extract just the database name from the URL
        db_name = database_url.rsplit("/", 1)[1].split("?")[0]  # Handle query params

        # Use autocommit mode to avoid transaction issues with DDL
        with admin_engine.connect() as conn:
            # Set autocommit mode
            conn.execution_options(isolation_level="AUTOCOMMIT")

            # Terminate existing connections
            conn.execute(
                text(
                    f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
                )
            )

            # Drop and create database (these commands will run outside transaction)
            conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
            conn.execute(text(f"CREATE DATABASE {db_name}"))

        logger.info("Test database created successfully")
        engine = create_engine(database_url)

    # Create all tables
    SQLModel.metadata.create_all(engine)
    yield engine

    # Clean up: drop all tables but keep the database
    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def db_session(db_engine):
    """Create database session for testing"""
    with Session(db_engine) as session:
        try:
            logger.debug(f"Test session using database: {db_engine.url}")
            yield session
            session.rollback()  # Roll back any uncommitted changes
        finally:
            session.close()


@pytest.fixture(autouse=True)
def init_test_db(db_session):
    """Initialize test database with basic data and unassigned league"""
    from backend.docker_utils.init_db import populate_database

    populate_database(db_session.get_bind())

    # Ensure unassigned league exists
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


@pytest.fixture
def client(db_session) -> TestClient:
    """Create TestClient with test database session"""
    def get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = get_test_db
    return TestClient(app)


@pytest.fixture
def admin_token(db_session: Session) -> str:
    """Create admin user and return admin token"""
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
    """Create test team with league assignment and return team token"""
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
        team_name = f"demo_team_{i}"
        team = db_session.exec(select(Team).where(Team.name == team_name)).first()

        if not team:
            # Create the Team with is_demo flag
            team = Team(
                name=team_name + "_demo",
                school_name=team_name,
                password_hash="test_hash",
                league_id=unassigned.id,
                is_demo=True,
                team_type=TeamType.STUDENT,
            )
            db_session.add(team)
            db_session.commit()
            db_session.refresh(team)

            # Create separate DemoUser tracking record
            demo_user = DemoUser(
                username=team_name,
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
