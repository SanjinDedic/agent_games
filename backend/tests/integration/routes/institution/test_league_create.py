from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, League
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def institution_token(db_session: Session) -> str:
    """Create an institution token for testing"""
    # First create an institution
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

    # Create and return token
    return create_access_token(
        data={
            "sub": institution.name,
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(minutes=30),
    )


@pytest.fixture
def institution_headers(institution_token: str) -> dict:
    """Return headers with institution authentication"""
    return {"Authorization": f"Bearer {institution_token}"}


def test_league_create_success(client, institution_headers, db_session):
    """Test successful league creation"""
    # Test basic league creation
    response = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={"name": "new_test_league", "game": "greedy_pig"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "league_id" in data["data"]
    assert data["data"]["name"] == "new_test_league"

    # Verify league was created in database
    league = db_session.exec(
        select(League).where(League.name == "new_test_league")
    ).first()
    assert league is not None
    assert league.game == "greedy_pig"


def test_league_create_failures(client, institution_headers, db_session):
    """Test failure cases for league creation"""
    # Test case 1: Duplicate league name
    # First create a league
    response = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={"name": "duplicate_league", "game": "greedy_pig"},
    )
    assert response.status_code == 200

    # Try to create league with same name
    response = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={"name": "duplicate_league", "game": "greedy_pig"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "already exists" in data["message"].lower()

    # Test case 2: Invalid game name
    response = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={"name": "invalid_game_league", "game": "invalid_game"},
    )
    assert response.status_code == 422
    assert "Game must be one of" in str(response.json())

    # Test case 3: Empty league name
    response = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={"name": "", "game": "greedy_pig"},
    )
    assert response.status_code == 422

    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/institution/league-create",
        json={"name": "unauthorized_league", "game": "greedy_pig"},
    )
    assert response.status_code == 401

    # Test case 5: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/institution/league-create",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={"name": "wrong_role_league", "game": "greedy_pig"},
    )
    assert response.status_code == 403