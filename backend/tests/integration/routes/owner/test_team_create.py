from datetime import timedelta

import pytest
from sqlmodel import Session, select


from backend.database.db_models import Team
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def owner_setup(db_session: Session) -> tuple:
    """Return owner token and headers."""
    db_session.commit()

    # Create token
    token = create_access_token(
        data={
            "sub": "test_owner",
            "role": "owner",
        },
        expires_delta=timedelta(minutes=30),
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    return token, headers


def test_team_create_success(client, owner_setup, db_session):
    """Test successful team creation"""
    _, headers = owner_setup
    
    # Test basic team creation
    response = client.post(
        "/owner/team-create",
        headers=headers,
        json={
            "name": "test_team",
            "password": "test_password",
            "school_name": "Test School",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "team_id" in data
    assert data["name"] == "test_team"

    # Verify team was created in database
    team = db_session.exec(select(Team).where(Team.name == "test_team")).first()
    assert team is not None
    assert team.school_name == "Test School"

    # Test team creation with optional fields
    response = client.post(
        "/owner/team-create",
        headers=headers,
        json={
            "name": "team_with_options",
            "password": "test_password",
            "school_name": "Option School",
            "color": "rgb(255,0,0)",
            "score": 100,
        },
    )
    assert response.status_code == 200


def test_team_create_failures(client, owner_setup, db_session):
    """Test failure cases for team creation"""
    _, headers = owner_setup
    
    # Test case 1: First create a team
    response = client.post(
        "/owner/team-create",
        headers=headers,
        json={
            "name": "duplicate_team",
            "password": "test_password",
            "school_name": "Test School",
        },
    )
    assert response.status_code == 200

    # Test duplicate team name
    response = client.post(
        "/owner/team-create",
        headers=headers,
        json={
            "name": "duplicate_team",
            "password": "different_password",
            "school_name": "Different School",
        },
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()

    # Test case 2: Missing required fields
    response = client.post(
        "/owner/team-create",
        headers=headers,
        json={"name": "incomplete_team"},  # Missing password
    )
    assert response.status_code == 422

    # Test case 3: Empty team name
    response = client.post(
        "/owner/team-create",
        headers=headers,
        json={"name": "", "password": "test_password"},
    )
    assert response.status_code == 422

    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/owner/team-create",
        json={
            "name": "unauthorized_team",
            "password": "test_password",
            "school_name": "Test School",
        },
    )
    assert response.status_code == 401

    # Test case 5: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/owner/team-create",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={
            "name": "wrong_role_team",
            "password": "test_password",
            "school_name": "Test School",
        },
    )
    assert response.status_code == 403


def test_team_create_name_must_be_globally_unique(client, owner_headers, db_session):
    """Team names are unique across the whole deployment.

    They used to be unique only within an institution. The constraint and the
    conflict check in create_team have to agree on that scope: if the check were
    narrower than the constraint, this second request would pass the check and
    then fail on insert as a 500 instead of a clean 409.
    """
    payload = {"name": "shared_team_name", "password": "pass", "school_name": "School A"}
    assert client.post("/owner/team-create", headers=owner_headers, json=payload).status_code == 200

    clash = client.post(
        "/owner/team-create",
        headers=owner_headers,
        json={"name": "shared_team_name", "password": "pass", "school_name": "School B"},
    )
    assert clash.status_code == 409

    teams = db_session.exec(select(Team).where(Team.name == "shared_team_name")).all()
    assert len(teams) == 1


def test_team_create_duplicate_rejected(client, owner_headers):
    """A name already in use is rejected with a 409."""
    payload = {"name": "same_team", "password": "pass", "school_name": "School"}
    first = client.post("/owner/team-create", headers=owner_headers, json=payload)
    assert first.status_code == 200

    second = client.post("/owner/team-create", headers=owner_headers, json=payload)
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"].lower()
