from datetime import timedelta

from sqlmodel import select

from backend.database.db_models import Institution, League
from backend.routes.auth.auth_core import create_access_token


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
    assert "league_id" in data
    assert data["name"] == "new_test_league"

    # Verify league was created in database
    league = db_session.exec(
        select(League).where(League.name == "new_test_league")
    ).first()
    assert league is not None
    assert league.game == "greedy_pig"

    # A new league runs until the institution's membership ends
    institution = db_session.get(Institution, league.institution_id)
    assert (
        abs(
            (
                league.expiry_date
                - institution.subscription.subscription_expiry
            ).total_seconds()
        )
        < 1
    )


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
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()

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