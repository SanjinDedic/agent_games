from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, Team
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def institution_setup(db_session: Session) -> tuple:
    """Setup institution for testing and return token and headers"""
    # Create an institution
    institution = Institution(
        name="test_institution",
        contact_person="Test Person",
        contact_email="test@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="test_hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    # Create token
    token = create_access_token(
        data={
            "sub": institution.name,
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(minutes=30),
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    return institution, token, headers


def test_team_create_success(client, institution_setup, db_session):
    """Test successful team creation"""
    institution, _, headers = institution_setup
    
    # Test basic team creation
    response = client.post(
        "/institution/team-create",
        headers=headers,
        json={
            "name": "test_team",
            "password": "test_password",
            "school_name": "Test School",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "team_id" in data["data"]
    assert data["data"]["name"] == "test_team"

    # Verify team was created in database
    team = db_session.exec(select(Team).where(Team.name == "test_team")).first()
    assert team is not None
    assert team.school_name == "Test School"
    assert team.institution_id == institution.id

    # Test team creation with optional fields
    response = client.post(
        "/institution/team-create",
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
    data = response.json()
    assert data["status"] == "success"


def test_team_create_failures(client, institution_setup, db_session):
    """Test failure cases for team creation"""
    _, _, headers = institution_setup
    
    # Test case 1: First create a team
    response = client.post(
        "/institution/team-create",
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
        "/institution/team-create",
        headers=headers,
        json={
            "name": "duplicate_team",
            "password": "different_password",
            "school_name": "Different School",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "already exists" in data["message"].lower()

    # Test case 2: Missing required fields
    response = client.post(
        "/institution/team-create",
        headers=headers,
        json={"name": "incomplete_team"},  # Missing password
    )
    assert response.status_code == 422

    # Test case 3: Empty team name
    response = client.post(
        "/institution/team-create",
        headers=headers,
        json={"name": "", "password": "test_password"},
    )
    assert response.status_code == 422

    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/institution/team-create",
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
        "/institution/team-create",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={
            "name": "wrong_role_team",
            "password": "test_password",
            "school_name": "Test School",
        },
    )
    assert response.status_code == 403