from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, League
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def signup_link_setup(db_session: Session) -> tuple:
    """Setup institution and league for testing signup link generation"""
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
    
    # Create a league
    league = League(
        name="signup_test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    
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
    
    return institution, league, token, headers


def test_generate_signup_link_success(client, signup_link_setup, db_session):
    """Test successful signup link generation"""
    institution, league, _, headers = signup_link_setup
    
    # Initially, league should have no signup link
    original_signup_link = league.signup_link
    
    # Generate signup link
    response = client.post(
        "/institution/generate-signup-link",
        headers=headers,
        json={"league_id": league.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "signup_token" in data["data"]
    
    # Verify link was saved to database
    db_session.refresh(league)
    assert league.signup_link is not None
    assert league.signup_link != original_signup_link
    assert league.signup_link == data["data"]["signup_token"]
    
    # Test regenerating link
    response = client.post(
        "/institution/generate-signup-link",
        headers=headers,
        json={"league_id": league.id},
    )
    assert response.status_code == 200
    new_data = response.json()
    assert new_data["status"] == "success"
    assert new_data["data"]["signup_token"] != data["data"]["signup_token"]
    
    # Verify new link was saved
    db_session.refresh(league)
    assert league.signup_link == new_data["data"]["signup_token"]


def test_generate_signup_link_failures(client, signup_link_setup, db_session):
    """Test failure cases for signup link generation"""
    institution, league, _, headers = signup_link_setup
    
    # Test case 1: Non-existent league
    response = client.post(
        "/institution/generate-signup-link",
        headers=headers,
        json={"league_id": 99999},
    )
    assert response.status_code == 200  # API returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    
    # Test case 2: League from different institution
    # Create another institution
    other_institution = Institution(
        name="other_institution",
        contact_person="Other Person",
        contact_email="other@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="test_hash",
    )
    db_session.add(other_institution)
    db_session.commit()
    
    # Create league for other institution
    other_league = League(
        name="other_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=other_institution.id,
    )
    db_session.add(other_league)
    db_session.commit()
    
    # Try to generate link for other institution's league
    response = client.post(
        "/institution/generate-signup-link",
        headers=headers,
        json={"league_id": other_league.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "permission" in data["message"].lower()
    
    # Test case 3: Missing league_id
    response = client.post(
        "/institution/generate-signup-link",
        headers=headers,
        json={},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "required" in data["message"].lower() or "league id" in data["message"].lower()
    
    # Test case 4: Invalid league_id type
    response = client.post(
        "/institution/generate-signup-link",
        headers=headers,
        json={"league_id": "not_an_integer"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    # The actual error message contains "League with ID not_an_integer not found" instead of "league_id"
    assert "id" in data["message"].lower() and "not found" in data["message"].lower()
    
    # Test case 5: Unauthorized access (no token)
    response = client.post(
        "/institution/generate-signup-link",
        json={"league_id": league.id},
    )
    assert response.status_code == 401