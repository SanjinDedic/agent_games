import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Generator

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
from backend.docker_utils.containers import ensure_containers_running
from backend.routes.auth.auth_core import create_access_token

os.environ["TESTING"] = "1"
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def verify_containers() -> tuple[bool, str]:
    """
    Verify both containers are running and healthy.
    Returns (True, "") if both containers are healthy,
    (False, error_message) otherwise
    """
    try:

        async def check_containers():
            async with httpx.AsyncClient() as client:
                validator = await client.get(
                    "http://localhost:8001/health", timeout=2.0
                )
                simulator = await client.get(
                    "http://localhost:8002/health", timeout=2.0
                )
                both_running = (
                    validator.status_code == 200
                    and simulator.status_code == 200
                    and validator.json()["status"] == "healthy"
                    and simulator.json()["status"] == "healthy"
                )
                if not both_running:
                    validator_status = f"Validator: {validator.status_code}"
                    simulator_status = f"Simulator: {simulator.status_code}"
                    return (
                        False,
                        f"Unhealthy containers - {validator_status}, {simulator_status}",
                    )
                return True, ""

        import asyncio

        healthy, msg = asyncio.run(check_containers())
        if healthy:
            logger.info("Container health check passed")
        else:
            logger.error(f"Container health check failed: {msg}")
        return healthy, msg

    except Exception as e:
        error_msg = f"Container verification failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


@pytest.fixture(scope="session", autouse=True)
def docker_environment():
    """Primary fixture for Docker container management"""
    logger.info("Starting Docker containers for test session")
    ensure_containers_running()

    # Initial health check
    is_healthy, msg = verify_containers()
    if not is_healthy:
        logger.error(f"Initial container health check failed: {msg}")
        pytest.fail(f"Container setup failed: {msg}")

    yield

    logger.info("Test session complete - containers will remain running")


@pytest.fixture
def ensure_containers(request):
    """
    Fixture for tests that require containers.
    Verifies containers are healthy before each test.
    """
    logger.info(f"Verifying containers for test: {request.node.name}")
    is_healthy, msg = verify_containers()
    if not is_healthy:
        pytest.fail(f"Containers not healthy before test {request.node.name}: {msg}")
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
