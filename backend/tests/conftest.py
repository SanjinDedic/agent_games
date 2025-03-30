import asyncio
import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple

import httpx
import pytest
import pytz
from fastapi.testclient import TestClient
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
from backend.docker_utils.compose_utils import (
    ensure_services_running,
    verify_all_services_healthy,
)
from backend.routes.auth.auth_core import create_access_token

os.environ["TESTING"] = "1"
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def run_docker_compose_build() -> bool:
    """Build Docker Compose services from scratch if images don't exist"""
    try:
        # Check if images exist
        result = subprocess.run(
            ["docker-compose", "images", "-q"],
            capture_output=True,
            text=True,
            check=False,
        )

        if not result.stdout.strip():
            logger.info("Docker images not found, building from scratch...")
            build_result = subprocess.run(
                ["docker-compose", "build"], capture_output=True, text=True, check=False
            )

            if build_result.returncode != 0:
                logger.error(f"Failed to build Docker images: {build_result.stderr}")
                return False

            logger.info("Docker images built successfully")

        return True

    except Exception as e:
        logger.error(f"Error checking or building Docker images: {e}")
        return False


def verify_containers() -> Tuple[bool, str]:
    """
    Verify validator and simulator services are running and healthy.
    Returns (True, "") if services are healthy, (False, error_message) otherwise
    """
    try:
        # First check if the services exist in docker-compose.yml
        config_result = subprocess.run(
            ["docker-compose", "config", "--services"],
            capture_output=True,
            text=True,
            check=False,
        )

        if config_result.returncode != 0:
            return False, f"Failed to get docker-compose config: {config_result.stderr}"

        all_services = config_result.stdout.strip().split("\n")
        if "validator" not in all_services or "simulator" not in all_services:
            return (
                False,
                f"Required services not found in docker-compose.yml: {all_services}",
            )

        # Check if services are running
        ps_result = subprocess.run(
            ["docker-compose", "ps", "--services", "--filter", "status=running"],
            capture_output=True,
            text=True,
            check=False,
        )

        if ps_result.returncode != 0:
            return False, f"Failed to get running services: {ps_result.stderr}"

        running_services = (
            ps_result.stdout.strip().split("\n") if ps_result.stdout.strip() else []
        )

        not_running = []
        if "validator" not in running_services:
            not_running.append("validator")
        if "simulator" not in running_services:
            not_running.append("simulator")

        if not_running:
            return False, f"Services not running: {', '.join(not_running)}"

        # Additional health check via HTTP endpoints
        async def check_services():
            async with httpx.AsyncClient() as client:
                try:
                    validator = await client.get(
                        "http://localhost:8001/health", timeout=2.0
                    )
                    simulator = await client.get(
                        "http://localhost:8002/health", timeout=2.0
                    )

                    validator_healthy = (
                        validator.status_code == 200
                        and validator.json().get("status") == "healthy"
                    )

                    simulator_healthy = (
                        simulator.status_code == 200
                        and simulator.json().get("status") == "healthy"
                    )

                    if not validator_healthy or not simulator_healthy:
                        validator_status = (
                            f"Validator: OK"
                            if validator_healthy
                            else f"Validator: Error ({validator.status_code})"
                        )
                        simulator_status = (
                            f"Simulator: OK"
                            if simulator_healthy
                            else f"Simulator: Error ({simulator.status_code})"
                        )
                        return (
                            False,
                            f"Services not healthy - {validator_status}, {simulator_status}",
                        )

                    return True, ""

                except Exception as e:
                    return False, f"Error connecting to service endpoints: {str(e)}"

        health_check_result = asyncio.run(check_services())
        return health_check_result

    except Exception as e:
        error_msg = f"Container verification failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def start_containers_with_polling(max_attempts=10, poll_interval=5) -> Tuple[bool, str]:
    """
    Start containers and poll until they're healthy or max attempts is reached
    Returns (True, "") on success, (False, error_message) on failure
    """
    try:
        # First, make sure we have the necessary Docker images
        if not run_docker_compose_build():
            return False, "Failed to build Docker images"

        # Start services
        start_result = subprocess.run(
            ["docker-compose", "up", "-d"], capture_output=True, text=True, check=False
        )

        if start_result.returncode != 0:
            return False, f"Failed to start services: {start_result.stderr}"

        logger.info("Services started, verifying health...")

        # Poll until services are healthy or max attempts is reached
        for attempt in range(1, max_attempts + 1):
            is_healthy, message = verify_containers()

            if is_healthy:
                logger.info(f"All services healthy after {attempt} attempts")
                return True, ""

            logger.info(
                f"Services not ready (attempt {attempt}/{max_attempts}): {message}"
            )

            if attempt < max_attempts:
                logger.info(f"Waiting {poll_interval} seconds before next check...")
                time.sleep(poll_interval)

        # If we get here, we've exceeded max attempts
        return False, f"Services failed to become healthy after {max_attempts} attempts"

    except Exception as e:
        error_msg = f"Error starting or polling containers: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


@pytest.fixture(scope="session", autouse=True)
def docker_environment():
    """
    Primary fixture for Docker container management
    Ensures containers are built (if needed) and running for the test session
    """
    logger.info("Setting up Docker environment for test session")

    # Start containers with polling for health
    is_ready, message = start_containers_with_polling(max_attempts=12, poll_interval=5)

    if not is_ready:
        logger.error(f"Failed to start Docker services: {message}")
        pytest.fail(f"Docker environment setup failed: {message}")

    logger.info("Docker environment ready for testing")

    yield

    logger.info("Test session complete - containers will remain running")

@pytest.fixture
def ensure_containers(request):
    """
    Fixture for tests that require containers.
    Verifies containers are healthy before each test,
    and attempts to restart them if needed.
    """
    test_name = request.node.name
    logger.info(f"Verifying containers for test: {test_name}")

    is_healthy, message = verify_containers()

    if not is_healthy:
        logger.warning(f"Containers not healthy for test {test_name}: {message}")
        logger.info("Attempting to restart containers...")

        # Try restarting the services
        restart_result = subprocess.run(
            ["docker-compose", "restart"], capture_output=True, text=True, check=False
        )

        if restart_result.returncode != 0:
            logger.error(f"Failed to restart services: {restart_result.stderr}")
            pytest.fail(f"Could not restart services: {restart_result.stderr}")

        # Give services time to restart and check again
        time.sleep(10)
        is_healthy, message = verify_containers()

        if not is_healthy:
            logger.error(f"Services still not healthy after restart: {message}")
            pytest.fail(f"Services not healthy for test {test_name}: {message}")

    logger.info(f"Services healthy for test: {test_name}")
    return True


@pytest.fixture
def db_engine():
    """Create a new database engine for testing"""
    engine = create_engine(get_database_url())
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
    with Session(db_engine) as session:
        try:
            print(f"Test session using database: {db_engine.url}")
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
def admin_token(db_session) -> str:
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
def test_league(db_session) -> League:
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
def auth_headers(admin_token) -> Dict[str, str]:
    """Return headers with admin authentication"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def team_auth_headers(team_token) -> Dict[str, str]:
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
