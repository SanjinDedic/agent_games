import logging
import os
from datetime import datetime, timedelta

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
    restart_service,
    verify_all_services_healthy,
    wait_for_services,
)
from backend.routes.auth.auth_core import create_access_token

os.environ["TESTING"] = "1"
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def docker_environment():
    """
    Primary fixture for Docker container management.
    Ensures containers are built (if needed) and running for the test session.
    """
    logger.info("Setting up Docker environment for test session")

    # Run docker compose build if needed (this happens automatically in docker compose up)
    # Then start and wait for services to be healthy
    is_ready = wait_for_services(timeout=60, interval=5)

    if not is_ready:
        is_healthy, statuses = verify_all_services_healthy()
        status_details = "\n".join(
            [f"- {svc}: {status}" for svc, status in statuses.items()]
        )
        logger.error(f"Services health check failed:\n{status_details}")
        pytest.fail("Docker environment setup failed - services not healthy")

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

    is_healthy, statuses = verify_all_services_healthy()

    if not is_healthy:
        # Log which services are unhealthy
        unhealthy = [
            f"{svc}: {status}"
            for svc, status in statuses.items()
            if "not healthy" in status.lower()
        ]
        logger.warning(
            f"Containers not healthy for test {test_name}: {', '.join(unhealthy)}"
        )
        logger.info("Attempting to restart containers...")

        # Restart services
        restart_success = restart_service()
        if not restart_success:
            logger.error("Failed to restart services")
            pytest.fail("Could not restart services")

        # Wait for services to become healthy
        is_ready = wait_for_services(timeout=30, interval=5)
        if not is_ready:
            is_healthy, statuses = verify_all_services_healthy()
            status_details = "\n".join(
                [f"- {svc}: {status}" for svc, status in statuses.items()]
            )
            logger.error(f"Services still not healthy after restart:\n{status_details}")
            pytest.fail(f"Services not healthy for test {test_name}")

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
