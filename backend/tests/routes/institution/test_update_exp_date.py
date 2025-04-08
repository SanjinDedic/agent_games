from datetime import datetime, timedelta

import pytest
import pytz
from sqlmodel import Session, select

from backend.database.db_models import Institution, League
from backend.routes.auth.auth_core import create_access_token

# Define the timezone used in your application
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")

@pytest.fixture
def expiry_setup(db_session: Session) -> tuple:
    """Setup institution and league for testing expiry updates"""
    # Create an institution with timezone-aware dates
    institution = Institution(
        name="test_institution",
        contact_person="Test Person",
        contact_email="test@example.com",
        created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
        subscription_active=True,
        subscription_expiry=datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=30),
        docker_access=True,
        password_hash="test_hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    # Create a league with timezone-aware dates
    league = League(
        name="expiry_test_league",
        created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
        expiry_date=datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=1),
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


def test_update_expiry_date_success(client, expiry_setup, db_session):
    """Test successful league expiry date updates"""
    institution, league, _, headers = expiry_setup

    # Initial expiry date
    initial_expiry = league.expiry_date

    # Test case 1: Update expiry to future date - use timezone-aware datetime
    new_expiry = datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=14)
    response = client.post(
        "/institution/update-expiry-date",
        headers=headers,
        json={
            "league": league.name,
            "date": new_expiry.isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "updated successfully" in data["message"]

    # Verify expiry date was updated
    db_session.refresh(league)
    # Compare dates with tolerance for small differences in timestamps
    assert abs((league.expiry_date - new_expiry).total_seconds()) < 5
    assert league.expiry_date > initial_expiry

    # Test case 2: Change to an even later date - use timezone-aware datetime
    later_expiry = datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=30)
    response = client.post(
        "/institution/update-expiry-date",
        headers=headers,
        json={
            "league": league.name,
            "date": later_expiry.isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify expiry date was updated again
    db_session.refresh(league)
    assert abs((league.expiry_date - later_expiry).total_seconds()) < 5
    assert league.expiry_date > new_expiry


def test_update_expiry_date_failures(client, expiry_setup, db_session):
    """Test failure cases for updating expiry date"""
    institution, league, _, headers = expiry_setup

    # Test case 1: Non-existent league
    new_expiry = datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(
        days=7
    )  # Use timezone-aware
    response = client.post(
        "/institution/update-expiry-date",
        headers=headers,
        json={
            "league": "non_existent_league",
            "date": new_expiry.isoformat(),
        },
    )
    assert response.status_code == 200  # API returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()

    # Test case 2: Past expiry date - use timezone-aware datetime
    past_date = datetime.now(AUSTRALIA_SYDNEY_TZ) - timedelta(days=1)
    response = client.post(
        "/institution/update-expiry-date",
        headers=headers,
        json={
            "league": league.name,
            "date": past_date.isoformat(),
        },
    )
    assert response.status_code == 422  # Validation error

    # Test case 3: Invalid date format
    response = client.post(
        "/institution/update-expiry-date",
        headers=headers,
        json={
            "league": league.name,
            "date": "not-a-date",
        },
    )
    assert response.status_code == 422

    # Test case 4: Empty league name
    response = client.post(
        "/institution/update-expiry-date",
        headers=headers,
        json={
            "league": "",
            "date": new_expiry.isoformat(),
        },
    )
    assert response.status_code == 422

    # Test case 5: League from different institution
    # Create another institution and league with timezone-aware dates
    other_institution = Institution(
        name="other_institution",
        contact_person="Other Person",
        contact_email="other@example.com",
        created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
        subscription_active=True,
        subscription_expiry=datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=30),
        docker_access=True,
        password_hash="test_hash",
    )
    db_session.add(other_institution)
    db_session.commit()

    other_league = League(
        name="other_league",
        created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
        expiry_date=datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=1),
        game="greedy_pig",
        institution_id=other_institution.id,
    )
    db_session.add(other_league)
    db_session.commit()

    # Try to update expiry for other institution's league
    response = client.post(
        "/institution/update-expiry-date",
        headers=headers,
        json={
            "league": other_league.name,
            "date": new_expiry.isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"

    # Test case 6: Unauthorized access (no token)
    response = client.post(
        "/institution/update-expiry-date",
        json={
            "league": league.name,
            "date": new_expiry.isoformat(),
        },
    )
    assert response.status_code == 401

    # Test case 7: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/institution/update-expiry-date",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={
            "league": league.name,
            "date": new_expiry.isoformat(),
        },
    )
    assert response.status_code == 403
