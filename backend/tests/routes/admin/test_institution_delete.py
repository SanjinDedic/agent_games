from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, League, Team
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def delete_institution_setup(db_session: Session) -> Institution:
    """Create an institution with leagues and teams for deletion testing"""
    # Create the institution
    institution = Institution(
        name="delete_test_institution",
        contact_person="Delete Test Contact",
        contact_email="delete@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="test_hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)
    
    # Create a league for the institution
    league = League(
        name="delete_test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()
    
    # Create a team in the league
    team = Team(
        name="delete_test_team",
        school_name="Delete Test School",
        password_hash="test_hash",
        league_id=league.id,
        institution_id=institution.id,
    )
    db_session.add(team)
    db_session.commit()
    
    return institution


def test_institution_delete_success(client, auth_headers, delete_institution_setup, db_session):
    """Test successful institution deletion"""
    institution = delete_institution_setup
    
    # Verify institution, league, and team exist before deletion
    assert db_session.exec(
        select(Institution).where(Institution.id == institution.id)
    ).first() is not None
    
    league = db_session.exec(
        select(League).where(League.institution_id == institution.id)
    ).first()
    assert league is not None
    
    team = db_session.exec(
        select(Team).where(Team.institution_id == institution.id)
    ).first()
    assert team is not None
    
    # Delete the institution
    response = client.post(
        "/admin/institution-delete",
        headers=auth_headers,
        json={"id": institution.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "institution" in data["message"].lower()
    assert "deleted" in data["message"].lower()
    
    # Verify institution was deleted
    assert db_session.exec(
        select(Institution).where(Institution.id == institution.id)
    ).first() is None
    
    # Verify related leagues were deleted
    assert db_session.exec(
        select(League).where(League.institution_id == institution.id)
    ).first() is None
    
    # Verify related teams were deleted
    assert db_session.exec(
        select(Team).where(Team.institution_id == institution.id)
    ).first() is None


def test_institution_delete_failures(client, auth_headers, db_session):
    """Test failure cases for institution deletion"""
    # Test case 1: Non-existent institution
    response = client.post(
        "/admin/institution-delete",
        headers=auth_headers,
        json={"id": 99999},  # Non-existent ID
    )
    assert response.status_code == 200  # API returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    
    # Test case 2: Missing ID
    response = client.post(
        "/admin/institution-delete",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 422
    
    # Test case 3: Invalid ID type
    response = client.post(
        "/admin/institution-delete",
        headers=auth_headers,
        json={"id": "not_an_integer"},
    )
    assert response.status_code == 422
    
    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/admin/institution-delete",
        json={"id": 1},
    )
    assert response.status_code == 401
    
    # Test case 5: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "institution"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/admin/institution-delete",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={"id": 1},
    )
    assert response.status_code == 403