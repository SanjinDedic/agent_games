import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.config import DEMO_TOKEN_EXPIRY
from backend.database.db_models import DemoUser, League, Team
from backend.routes.auth.auth_core import create_access_token
from backend.routes.demo.demo_db import create_demo_user, ensure_demo_leagues_exist


@pytest.fixture
def demo_token() -> str:
    """Create a demo token for testing"""
    return create_access_token(
        data={
            "sub": "test_demo_user",
            "role": "student",
            "is_demo": True,
            "exp_time": DEMO_TOKEN_EXPIRY,
        },
        expires_delta=timedelta(minutes=DEMO_TOKEN_EXPIRY),
    )


@pytest.fixture
def demo_league(db_session: Session) -> League:
    """Create a test demo league"""
    league = db_session.exec(
        select(League).where(League.name == "greedy_pig_demo")
    ).first()

    if not league:
        league = League(
            name="greedy_pig_demo",
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=7),
            game="greedy_pig",
            is_demo=True,
        )
        db_session.add(league)
        db_session.commit()
        db_session.refresh(league)

    return league


@pytest.fixture
def demo_team(db_session: Session) -> Team:
    """Create a test demo team"""
    # Get or create unassigned league
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
        db_session.refresh(unassigned)

    # Create demo team
    team, _ = create_demo_user(db_session, "TestDemoUser")
    return team


def test_launch_demo_success(client: TestClient, db_session: Session):
    """Test successful demo launch without user info"""
    response = client.post("/demo/launch_demo")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "access_token" in data["data"]
    assert "username" in data["data"]
    assert "available_games" in data["data"]
    assert "demo_leagues" in data["data"]

    # Verify demo user was created in DB
    username = data["data"]["username"]
    team = db_session.exec(select(Team).where(Team.name == username)).first()
    assert team is not None
    assert team.is_demo is True


def test_launch_demo_with_user_info(client: TestClient, db_session: Session):
    """Test demo launch with provided user info"""
    response = client.post(
        "/demo/launch_demo",
        json={"username": "TestUser", "email": "test@example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "access_token" in data["data"]

    # Verify username was used
    assert "TestUser_Demo" in data["data"]["username"]

    # Verify DemoUser record was created
    demo_user = db_session.exec(
        select(DemoUser).where(DemoUser.username == "TestUser")
    ).first()
    assert demo_user is not None
    assert demo_user.email == "test@example.com"


def test_launch_demo_validation_errors(client: TestClient):
    """Test validation errors in demo launch"""
    # Test case 1: Username too long
    response = client.post(
        "/demo/launch_demo",
        json={
            "username": "ThisUsernameIsTooLongForTheSystem",
            "email": "test@example.com",
        },
    )
    assert response.status_code == 422

    # Test case 2: Invalid username (non-alphanumeric)
    response = client.post(
        "/demo/launch_demo",
        json={"username": "User@Name", "email": "test@example.com"},
    )
    assert response.status_code == 422

    # Test case 3: Invalid email
    response = client.post(
        "/demo/launch_demo",
        json={"username": "ValidName", "email": "not-an-email"},
    )
    assert response.status_code == 422


def test_demo_leagues_creation(client: TestClient, db_session: Session):
    """Test demo leagues are created properly"""
    # Call launch demo to trigger league creation
    response = client.post("/demo/launch_demo")
    assert response.status_code == 200

    # Verify demo leagues exist
    demo_leagues = db_session.exec(select(League).where(League.is_demo == True)).all()
    assert len(demo_leagues) > 0

    # Check league properties
    for league in demo_leagues:
        assert league.name.endswith("_demo")
        assert league.is_demo is True
        assert league.expiry_date > datetime.now()


def test_demo_authentication_lifecycle(client: TestClient, db_session: Session):
    """Test complete demo authentication lifecycle"""
    # 1. Launch demo to get token
    response = client.post("/demo/launch_demo")
    assert response.status_code == 200
    data = response.json()
    token = data["data"]["access_token"]

    # 2. Use token to access a non-demo endpoint that accepts student role
    response = client.get(
        "/user/get-all-leagues",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
