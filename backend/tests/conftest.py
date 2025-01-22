import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Generator

import pytest
from api import app
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from backend.database.db_config import get_database_url
from backend.database.db_models import Admin, League, Team, get_password_hash
from backend.database.db_session import get_db
from backend.docker_utils.containers import ensure_containers_running, stop_containers
from backend.routes.auth.auth_core import create_access_token

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set testing environment variable
os.environ["TESTING"] = "1"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Primary test environment setup fixture"""
    logger.info("Starting test environment setup")

    try:
        # Create test directories
        root_dir = Path(__file__).parent.parent
        test_dirs = {
            "prisoners": {
                "test": root_dir
                / "games"
                / "prisoners_dilemma"
                / "leagues"
                / "test_league",
                "admin": root_dir / "games" / "prisoners_dilemma" / "leagues" / "admin",
            },
            "greedy": {
                "test": root_dir / "games" / "greedy_pig" / "leagues" / "test_league",
                "admin": root_dir / "games" / "greedy_pig" / "leagues" / "admin",
            },
        }

        # Create directories
        for game_dirs in test_dirs.values():
            for path in game_dirs.values():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    if not path.exists():
                        raise RuntimeError(f"Failed to create directory: {path}")
                    logger.info(f"Verified directory exists: {path}")
                except Exception as e:
                    logger.error(f"Error creating directory {path}: {str(e)}")
                    raise

        # Start containers
        logger.info("Starting Docker containers")
        ensure_containers_running()

        # Allow container startup time
        time.sleep(5)  # Give containers time to fully start
        logger.info("Test environment setup completed successfully")

        yield test_dirs

        # Cleanup
        logger.info("Starting test environment cleanup")
        stop_containers()
        logger.info("Test environment cleanup completed")

    except Exception as e:
        logger.error(f"Error in test environment setup/teardown: {str(e)}")
        raise


@pytest.fixture
def db_engine():
    """Create a new database engine for testing"""
    engine = create_engine(get_database_url())
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a new database session for testing"""
    with Session(db_engine) as session:
        yield session


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

    access_token = create_access_token(
        data={"sub": "admin", "role": "admin"}, expires_delta=timedelta(minutes=30)
    )
    return access_token


@pytest.fixture
def team_token(db_session):
    """Create a test team with league assignment"""

    # First create and commit the league
    league = db_session.exec(select(League).where(League.name == "comp_test")).first()
    if not league:
        league = League(
            name="comp_test",
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=7),
            game="greedy_pig",
        )
        db_session.add(league)
        db_session.commit()  # Commit league first to get its ID

        # Refresh the league to ensure we have its ID
        db_session.refresh(league)

    # Now create the team with the committed league's ID
    team = Team(
        name="test_team",
        school_name="Test School",
        password_hash=get_password_hash("test_password"),
        league_id=league.id,  # Now league.id will be valid
    )
    db_session.add(team)
    db_session.commit()

    # Create and return token
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
    # Create unassigned league if it doesn't exist
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
