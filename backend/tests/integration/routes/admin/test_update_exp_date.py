from datetime import timedelta

import pytest
from sqlmodel import Session, select


from backend.database.db_models import League
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now

# Define the timezone used in your application

@pytest.fixture
def expiry_setup(db_session: Session) -> tuple:
    """Setup and league for testing expiry updates"""
    # Timezone-aware dates throughout
    db_session.commit()

    # Create a league with timezone-aware dates
    league = League(
        name="expiry_test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=1),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    # Create token
    token = create_access_token(
        data={
            "sub": "test_admin",
            "role": "admin",
        },
        expires_delta=timedelta(minutes=30),
    )

    headers = {"Authorization": f"Bearer {token}"}

    return league, token, headers


def test_update_expiry_date_success(client, expiry_setup, db_session):
    """Test successful league expiry date updates"""
    league, _, headers = expiry_setup

    # Initial expiry date
    initial_expiry = league.expiry_date

    # Test case 1: Update expiry to future date - use timezone-aware datetime
    new_expiry = utc_now() + timedelta(days=14)
    response = client.post(
        "/admin/update-expiry-date",
        headers=headers,
        json={
            "league_id": league.id,
            "date": new_expiry.isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "updated successfully" in data["message"]

    # Verify expiry date was updated
    db_session.refresh(league)
    # Compare dates with tolerance for small differences in timestamps
    assert abs((league.expiry_date - new_expiry).total_seconds()) < 5
    assert league.expiry_date > initial_expiry

    # Test case 2: Change to an even later date - use timezone-aware datetime
    later_expiry = utc_now() + timedelta(days=30)
    response = client.post(
        "/admin/update-expiry-date",
        headers=headers,
        json={
            "league_id": league.id,
            "date": later_expiry.isoformat(),
        },
    )
    assert response.status_code == 200

    # Verify expiry date was updated again
    db_session.refresh(league)
    assert abs((league.expiry_date - later_expiry).total_seconds()) < 5
    assert league.expiry_date > new_expiry


def test_update_expiry_date_failures(client, expiry_setup, db_session):
    """Test failure cases for updating expiry date"""
    league, _, headers = expiry_setup

    # Test case 1: Non-existent league
    new_expiry = utc_now() + timedelta(
        days=7
    )  # Use timezone-aware
    response = client.post(
        "/admin/update-expiry-date",
        headers=headers,
        json={
            "league_id": 99999,
            "date": new_expiry.isoformat(),
        },
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # Test case 2: Past expiry date - use timezone-aware datetime
    past_date = utc_now() - timedelta(days=1)
    response = client.post(
        "/admin/update-expiry-date",
        headers=headers,
        json={
            "league_id": league.id,
            "date": past_date.isoformat(),
        },
    )
    assert response.status_code == 422  # Validation error

    # Test case 3: Invalid date format
    response = client.post(
        "/admin/update-expiry-date",
        headers=headers,
        json={
            "league_id": league.id,
            "date": "not-a-date",
        },
    )
    assert response.status_code == 422

    # Test case 4: Missing league_id field
    response = client.post(
        "/admin/update-expiry-date",
        headers=headers,
        json={
            "date": new_expiry.isoformat(),
        },
    )
    assert response.status_code == 422

