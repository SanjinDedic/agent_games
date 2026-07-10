from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, League, Team
from backend.routes.auth.auth_core import create_access_token
from backend.routes.user.user_db import get_team_by_id
from backend.tests.conftest import make_student_token
from backend.time_utils import utc_now


@pytest.fixture
def test_institution(db_session: Session) -> Institution:
    """Get the Admin Institution created by conftest seed data"""
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()
    assert institution is not None, "Admin Institution not found"
    return institution


@pytest.fixture
def setup_leagues(db_session: Session, test_institution: Institution) -> dict:
    """Create test leagues for assignment testing"""
    leagues = {}

    # Create main test league
    comp_test = db_session.exec(
        select(League).where(League.name == "comp_test")
    ).first()

    if not comp_test:
        comp_test = League(
            name="comp_test",
            created_date=utc_now(),
            expiry_date=utc_now() + timedelta(days=7),
            game="greedy_pig",
            institution_id=test_institution.id,
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
            created_date=utc_now(),
            expiry_date=utc_now() + timedelta(days=7),
            game="prisoners_dilemma",
            institution_id=test_institution.id,
        )
        db_session.add(pd_league)
        db_session.commit()
        db_session.refresh(pd_league)
    leagues["pd_test"] = pd_league

    return leagues


@pytest.fixture
def setup_unassigned_team(db_session: Session, test_institution: Institution) -> Team:
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
            institution_id=test_institution.id,
        )
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)

    return team


@pytest.fixture
def student_token(setup_unassigned_team: Team) -> str:
    """Create a valid student token for the test team"""
    return make_student_token(setup_unassigned_team)


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
        json={"league_id": setup_leagues["comp_test"].id},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "assigned to league" in data["message"]
    # Successful assign returns a refreshed token carrying the new league_id.
    assert "access_token" in data
    from jose import jwt
    from backend.routes.auth.auth_config import ALGORITHM, SECRET_KEY
    payload = jwt.decode(data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["league_id"] == setup_leagues["comp_test"].id

    # Verify assignment in database
    team = get_team_by_id(db_session, setup_unassigned_team.id)
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
        json={"league_id": setup_leagues["pd_test"].id},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    assert "assigned to league" in response.json()["message"]

    # Verify assignment
    team = get_team_by_id(db_session, setup_unassigned_team.id)
    assert team.league.name == "pd_test"


def test_league_assign_exceptions(
    client, db_session: Session, student_token: str, setup_unassigned_team: Team
):
    """Test error cases for league assignment"""

    # Test case 1: Assign to non-existent league
    response = client.post(
        "/user/league-assign",
        json={"league_id": 99999},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # Verify team remains in original league
    team = get_team_by_id(db_session, setup_unassigned_team.id)
    assert team.league.name == "unassigned"

    # Test case 2: Unauthorized access (no token)
    response = client.post("/user/league-assign", json={"league_id": 1})
    assert response.status_code == 401

    # Test case 3: Invalid token
    invalid_token = "invalid.token.here"
    response = client.post(
        "/user/league-assign",
        json={"league_id": 1},
        headers={"Authorization": f"Bearer {invalid_token}"},
    )
    assert response.status_code == 401

    # Test case 4: Missing league_id field
    response = client.post(
        "/user/league-assign",
        json={},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 422


def test_get_all_leagues_success(client, student_token: str, setup_leagues: dict):
    """Test successful retrieval of all leagues"""

    response = client.get(
        "/user/get-all-leagues", headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 200

    # Verify league data
    leagues = response.json()["leagues"]
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
    assert "leagues" in response.json()
