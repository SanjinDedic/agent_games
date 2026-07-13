from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlmodel import Session, select

from backend.api import app
from backend.routes.auth.auth_config import (
    ALGORITHM,
    DEMO_TOKEN_EXPIRY_MINUTES,
    SECRET_KEY,
)
from backend.database.db_models import DemoUser, League, Team
from backend.routes.demo.demo_db import create_demo_user, get_or_create_demo_league
from backend.tests.conftest import make_student_token
from backend.time_utils import utc_now


@pytest.fixture
def demo_league(db_session: Session) -> League:
    """A demo league, created the same way the router creates it"""
    return get_or_create_demo_league(db_session, "greedy_pig")


@pytest.fixture
def demo_team(db_session: Session) -> Team:
    """A demo team, created the same way the router creates it"""
    return create_demo_user(db_session, "TestDemoUser")


@pytest.fixture
def demo_team_headers(demo_team: Team) -> dict:
    """Student headers for the demo team, carrying the is_demo claim"""
    return {"Authorization": f"Bearer {make_student_token(demo_team)}"}


def test_launch_demo_success(client: TestClient, db_session: Session):
    """Test successful demo launch without user info"""
    response = client.post("/demo/launch_demo")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "username" in data
    assert "available_games" in data
    assert "demo_leagues" in data

    # Verify demo user was created in DB
    username = data["username"]
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
    assert "access_token" in data

    # Verify username was used
    assert "TestUser_Demo" in data["username"]

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


def test_launch_demo_requires_unassigned_league(
    client: TestClient, db_session: Session
):
    """A missing 'unassigned' league is a broken seed invariant, so it 500s.

    The league is renamed rather than deleted because seeded teams FK-reference
    it; create_demo_user looks it up by name, so this is the state it guards.
    """
    unassigned = db_session.exec(
        select(League).where(League.name == "unassigned")
    ).one()
    unassigned.name = "unassigned_renamed"
    db_session.add(unassigned)
    db_session.commit()

    # The `client` fixture re-raises server exceptions; this one asserts the
    # response a real caller gets instead of a masked 200.
    non_raising_client = TestClient(app, raise_server_exceptions=False)
    response = non_raising_client.post("/demo/launch_demo")
    assert response.status_code == 500


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
        assert league.expiry_date > utc_now()


def test_demo_authentication_lifecycle(client: TestClient, db_session: Session):
    """Test complete demo authentication lifecycle"""
    # 1. Launch demo to get token
    response = client.post("/demo/launch_demo")
    assert response.status_code == 200
    data = response.json()
    token = data["access_token"]

    # 2. Use token to access a non-demo endpoint that accepts student role
    response = client.get(
        "/user/get-all-leagues",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "leagues" in response.json()


def test_demo_token_includes_institution_id(client: TestClient, db_session: Session):
    """Test that demo token includes institution_id so demo users can see demo leagues"""
    response = client.post("/demo/launch_demo")
    assert response.status_code == 200
    token = response.json()["access_token"]

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "institution_id" in payload, "Demo token must include institution_id"
    assert payload["institution_id"] is not None

    # Verify demo user can actually see demo leagues via the endpoint
    leagues_response = client.get(
        "/user/get-all-leagues",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert leagues_response.status_code == 200
    leagues = leagues_response.json()["leagues"]
    assert len(leagues) > 0, "Demo user should see demo leagues"


def test_launch_demo_token_expiry_matches_config(client: TestClient):
    """The token's exp and the advertised expiry both come from the demo config."""
    response = client.post("/demo/launch_demo")
    assert response.status_code == 200
    data = response.json()
    assert data["expires_in_minutes"] == DEMO_TOKEN_EXPIRY_MINUTES

    payload = jwt.decode(data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    expiry = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    expected = utc_now() + timedelta(minutes=DEMO_TOKEN_EXPIRY_MINUTES)
    assert abs((expiry - expected).total_seconds()) < 60


def test_demo_user_can_join_demo_league(
    client: TestClient, demo_team_headers: dict, demo_league: League
):
    """A demo user can assign itself to a demo league."""
    response = client.post(
        "/user/league-assign",
        headers=demo_team_headers,
        json={"league_id": demo_league.id},
    )
    assert response.status_code == 200
    assert "assigned to league" in response.json()["message"]


def test_demo_user_cannot_join_non_demo_league(
    client: TestClient, db_session: Session, demo_team: Team, demo_team_headers: dict
):
    """A demo user is confined to demo leagues, and a rejected join changes nothing."""
    real_league = db_session.exec(
        select(League).where(League.name == "greedy_pig_league")
    ).one()
    original_league_id = demo_team.league_id

    response = client.post(
        "/user/league-assign",
        headers=demo_team_headers,
        json={"league_id": real_league.id},
    )
    assert response.status_code == 403
    assert "demo" in response.json()["detail"].lower()

    db_session.refresh(demo_team)
    assert demo_team.league_id == original_league_id
