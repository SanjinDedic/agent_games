from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import League, Team
from backend.routes.auth.auth_core import create_access_token
from backend.routes.user.user_db import get_team


@pytest.fixture
def setup_leagues(db_session: Session) -> dict:
    """Create test leagues for assignment testing"""
    leagues = {}

    # Create main test league
    comp_test = db_session.exec(
        select(League).where(League.name == "comp_test")
    ).first()

    if not comp_test:
        comp_test = League(
            name="comp_test",
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=7),
            game="greedy_pig",
        )
        db_session.add(comp_test)
        db_session.commit()
        db_session.refresh(comp_test)
    leagues["comp_test"] = comp_test

    # Create test league with different game
    pd_league = db_session.exec(select(League).where(League.name == "pd_test")).first()

    if not pd_league:
        pd_league = League(
            name="pd_test",
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=7),
            game="prisoners_dilemma",
        )
        db_session.add(pd_league)
        db_session.commit()
        db_session.refresh(pd_league)
    leagues["pd_test"] = pd_league

    return leagues


@pytest.fixture
def setup_unassigned_team(db_session: Session) -> Team:
    """Create a test team in unassigned league"""
    # Get unassigned league
    unassigned = db_session.exec(
        select(League).where(League.name == "unassigned")
    ).first()

    assert unassigned is not None, "Unassigned league not found"

    # Create team if it doesn't exist
    team = db_session.exec(select(Team).where(Team.name == "test_assign_team")).first()

    if not team:
        team = Team(
            name="test_assign_team",
            school_name="Test School",
            password_hash="test_hash",
            league_id=unassigned.id,
        )
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)

    return team


@pytest.fixture
def student_token(setup_unassigned_team: Team) -> str:
    """Create a valid student token for the test team"""
    return create_access_token(
        data={"sub": setup_unassigned_team.name, "role": "student"},
        expires_delta=timedelta(minutes=30),
    )


def test_league_assign_success(
    client,
    db_session: Session,
    student_token: str,
    setup_leagues: dict,
    setup_unassigned_team: Team,
):
    """Test successful league assignment scenarios"""

    # Test case 1: Basic league assignment
    response = client.post(
        "/user/league-assign",
        json={"name": "comp_test"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "assigned to league" in data["message"]

    # Verify assignment in database
    team = get_team(db_session, setup_unassigned_team.name)
    assert team.league.name == "comp_test"

    # Test case 2: Assign to different league
    # First reset to unassigned
    unassigned = db_session.exec(
        select(League).where(League.name == "unassigned")
    ).first()
    team.league_id = unassigned.id
    db_session.commit()

    response = client.post(
        "/user/league-assign",
        json={"name": "pd_test"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "assigned to league" in data["message"]

    # Verify assignment
    team = get_team(db_session, setup_unassigned_team.name)
    assert team.league.name == "pd_test"


def test_league_assign_exceptions(
    client, db_session: Session, student_token: str, setup_unassigned_team: Team
):
    """Test error cases for league assignment"""

    # Test case 1: Assign to non-existent league
    response = client.post(
        "/user/league-assign",
        json={"name": "non_existent_league"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()

    # Verify team remains in original league
    team = get_team(db_session, setup_unassigned_team.name)
    assert team.league.name == "unassigned"

    # Test case 2: Unauthorized access (no token)
    response = client.post("/user/league-assign", json={"name": "comp_test"})
    assert response.status_code == 401

    # Test case 3: Invalid token
    invalid_token = "invalid.token.here"
    response = client.post(
        "/user/league-assign",
        json={"name": "comp_test"},
        headers={"Authorization": f"Bearer {invalid_token}"},
    )
    assert response.status_code == 401

    # Test case 4: Empty league name
    response = client.post(
        "/user/league-assign",
        json={"name": ""},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 422


def test_get_all_leagues_success(client, student_token: str, setup_leagues: dict):
    """Test successful retrieval of all leagues"""

    response = client.get(
        "/user/get-all-leagues", headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify league data
    leagues = data["data"]["leagues"]
    league_names = [league["name"] for league in leagues]
    assert "comp_test" in league_names
    assert "pd_test" in league_names
    assert "unassigned" in league_names

    # Verify league properties
    for league in leagues:
        assert "id" in league
        assert "name" in league
        assert "game" in league
        assert "created_date" in league
        assert "expiry_date" in league


def test_get_all_leagues_exceptions(client):
    """Test error cases for getting all leagues"""

    # Test case 1: Unauthorized access (no token)
    response = client.get("/user/get-all-leagues")
    assert response.status_code == 401

    # Test case 2: Invalid token
    invalid_token = "invalid.token.here"
    response = client.get(
        "/user/get-all-leagues", headers={"Authorization": f"Bearer {invalid_token}"}
    )
    assert response.status_code == 401

    # Test case 3: Admin access should work
    admin_token = create_access_token(
        data={"sub": "admin", "role": "admin"}, expires_delta=timedelta(minutes=30)
    )
    response = client.get(
        "/user/get-all-leagues", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
