from datetime import timedelta

import pytest
from sqlmodel import Session, select


from backend.database.db_models import League
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def signup_link_setup(db_session: Session) -> tuple:
    """Setup and league for testing signup link generation"""
    db_session.commit()
    
    # Create a league
    league = League(
        name="signup_test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    
    # Create token
    token = create_access_token(
        data={
            "sub": "test_owner",
            "role": "owner",
        },
        expires_delta=timedelta(minutes=30),
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    return league, token, headers


def test_generate_signup_link_success(client, signup_link_setup, db_session):
    """Test successful signup link generation"""
    league, _, headers = signup_link_setup

    # Initially, league should have no signup link
    original_signup_link = league.signup_link

    # Generate signup link
    response = client.post(
        "/owner/generate-signup-link",
        headers=headers,
        json={"league_id": league.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert "signup_token" in data

    # Verify link was saved to database
    db_session.refresh(league)
    assert league.signup_link is not None
    assert league.signup_link != original_signup_link
    assert league.signup_link == data["signup_token"]

    # Test regenerating link
    response = client.post(
        "/owner/generate-signup-link",
        headers=headers,
        json={"league_id": league.id},
    )
    assert response.status_code == 200
    new_data = response.json()
    assert new_data["signup_token"] != data["signup_token"]

    # Verify new link was saved
    db_session.refresh(league)
    assert league.signup_link == new_data["signup_token"]


def test_generate_signup_link_failures(client, signup_link_setup, db_session):
    """Test failure cases for signup link generation"""
    league, _, headers = signup_link_setup

    # Test case 1: Non-existent league
    response = client.post(
        "/owner/generate-signup-link",
        headers=headers,
        json={"league_id": 99999},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


    # Test case 3: Missing league_id (Pydantic 422)
    response = client.post(
        "/owner/generate-signup-link",
        headers=headers,
        json={},
    )
    assert response.status_code == 422

    # Test case 4: Invalid league_id type (Pydantic 422)
    response = client.post(
        "/owner/generate-signup-link",
        headers=headers,
        json={"league_id": "not_an_integer"},
    )
    assert response.status_code == 422
