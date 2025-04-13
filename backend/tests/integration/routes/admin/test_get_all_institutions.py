from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, League, Team
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def institutions_setup(db_session: Session) -> list:
    """Setup multiple institutions with leagues and teams for testing"""
    institutions = []
    
    # Create first institution with leagues and teams
    institution1 = Institution(
        name="first_institution",
        contact_person="First Contact",
        contact_email="first@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="test_hash",
    )
    db_session.add(institution1)
    db_session.commit()
    db_session.refresh(institution1)
    institutions.append(institution1)
    
    # Create a league for the first institution
    league1 = League(
        name="first_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution1.id,
    )
    db_session.add(league1)
    db_session.commit()
    
    # Create a team for the first institution
    team1 = Team(
        name="first_team",
        school_name="First School",
        password_hash="test_hash",
        league_id=league1.id,
        institution_id=institution1.id,
    )
    db_session.add(team1)
    db_session.commit()
    
    # Create second institution
    institution2 = Institution(
        name="second_institution",
        contact_person="Second Contact",
        contact_email="second@example.com",
        created_date=datetime.now(),
        subscription_active=False,  # Inactive
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=False,
        password_hash="test_hash",
    )
    db_session.add(institution2)
    db_session.commit()
    db_session.refresh(institution2)
    institutions.append(institution2)
    
    # Create third institution with expired subscription
    institution3 = Institution(
        name="third_institution",
        contact_person="Third Contact",
        contact_email="third@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() - timedelta(days=1),  # Expired
        docker_access=True,
        password_hash="test_hash",
    )
    db_session.add(institution3)
    db_session.commit()
    db_session.refresh(institution3)
    institutions.append(institution3)
    
    return institutions


def test_get_all_institutions_success(client, auth_headers, institutions_setup):
    """Test successful retrieval of all institutions"""
    institutions = institutions_setup
    
    # Get all institutions
    response = client.get(
        "/admin/get-all-institutions",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "institutions retrieved successfully" in data["message"].lower()
    
    # Verify the response contains all created institutions
    assert "institutions" in data["data"]
    institution_names = [inst["name"] for inst in data["data"]["institutions"]]
    for institution in institutions:
        assert institution.name in institution_names
    
    # Verify each institution has the expected fields
    for inst in data["data"]["institutions"]:
        assert "id" in inst
        assert "name" in inst
        assert "contact_person" in inst
        assert "contact_email" in inst
        assert "created_date" in inst
        assert "subscription_active" in inst
        assert "subscription_expiry" in inst
        assert "docker_access" in inst
        assert "team_count" in inst
        assert "league_count" in inst
    
    # Verify first institution has the expected team and league counts
    first_inst = next(
        inst for inst in data["data"]["institutions"]
        if inst["name"] == "first_institution"
    )
    assert first_inst["team_count"] == 1
    assert first_inst["league_count"] == 1
    
    # Verify inactive/expired institutions are still included
    inactive_names = ["second_institution", "third_institution"]
    for name in inactive_names:
        assert name in institution_names


def test_get_all_institutions_failures(client):
    """Test failure cases for getting all institutions"""
    # Test case 1: Unauthorized access (no token)
    response = client.get("/admin/get-all-institutions")
    assert response.status_code == 401
    
    # Test case 2: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "institution"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.get(
        "/admin/get-all-institutions",
        headers={"Authorization": f"Bearer {wrong_token}"},
    )
    assert response.status_code == 403
    
    # Test case 3: Expired token
    expired_token = create_access_token(
        data={"sub": "admin", "role": "admin"},
        expires_delta=timedelta(microseconds=1),  # Immediate expiration
    )
    import time
    time.sleep(0.01)  # Ensure token expiration
    response = client.get(
        "/admin/get-all-institutions",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401