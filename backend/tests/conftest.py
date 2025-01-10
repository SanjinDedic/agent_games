import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from datetime import datetime, timedelta
from typing import Dict, Generator

import pytest
from api import app
from config import get_database_url
from database.db_models import Admin, League, Team
from database.db_session import get_db
from fastapi.testclient import TestClient
from routes.auth.auth_core import create_access_token, get_password_hash
from sqlmodel import Session, SQLModel, create_engine, select

# Set testing environment variable
os.environ["TESTING"] = "1"


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
def team_token(db_session) -> str:
    """Create a test team and return a team token"""
    team = Team(
        name="test_team",
        school_name="Test School",
        password_hash=get_password_hash("test_password"),
    )
    db_session.add(team)
    db_session.commit()

    access_token = create_access_token(
        data={"sub": team.name, "role": "student"}, expires_delta=timedelta(minutes=30)
    )
    return access_token


@pytest.fixture
def test_league(db_session) -> League:
    """Create a test league"""
    league = League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=1),
        folder="leagues/test_league",
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
            folder="leagues/admin/unassigned",
            game="greedy_pig",
        )
        db_session.add(unassigned)
        db_session.commit()

    return unassigned
