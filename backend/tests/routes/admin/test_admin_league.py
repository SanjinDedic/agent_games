from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import League, SimulationResult, Team
from backend.routes.auth.auth_core import create_access_token


def test_create_league_success(client, auth_headers, db_session):
    """Test successful league creation scenarios"""

    # Test case 1: Basic league creation with greedy_pig game
    response = client.post(
        "/admin/league-create",
        headers=auth_headers,
        json={"name": "new_league", "game": "greedy_pig"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "league_id" in data["data"]

    # Verify league was created in database
    league = db_session.exec(select(League).where(League.name == "new_league")).first()
    assert league is not None
    assert league.game == "greedy_pig"
    assert league.expiry_date > datetime.now()

    # Test case 2: Create league with prisoners_dilemma game
    response = client.post(
        "/admin/league-create",
        headers=auth_headers,
        json={"name": "pd_league", "game": "prisoners_dilemma"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify league in database
    league = db_session.exec(select(League).where(League.name == "pd_league")).first()
    assert league is not None
    assert league.game == "prisoners_dilemma"


def test_create_league_exceptions(client, auth_headers, db_session):
    """Test all possible error cases for league creation"""

    # Test case 1: Duplicate league name
    # First create a league
    response = client.post(
        "/admin/league-create",
        headers=auth_headers,
        json={"name": "duplicate_league", "game": "greedy_pig"},
    )
    assert response.status_code == 200

    # Try to create league with same name
    response = client.post(
        "/admin/league-create",
        headers=auth_headers,
        json={"name": "duplicate_league", "game": "greedy_pig"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "already exists" in data["message"]

    # Test case 2: Invalid game name
    response = client.post(
        "/admin/league-create",
        headers=auth_headers,
        json={"name": "invalid_game_league", "game": "invalid_game"},
    )
    assert response.status_code == 422
    assert "Game must be one of" in str(response.json())

    # Test case 3: Empty league name
    response = client.post(
        "/admin/league-create",
        headers=auth_headers,
        json={"name": "", "game": "greedy_pig"},
    )
    assert response.status_code == 422

    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/admin/league-create",
        json={"name": "unauthorized_league", "game": "greedy_pig"},
    )
    assert response.status_code == 401

    # Test case 5: Non-admin token
    non_admin_token = create_access_token(
        data={"sub": "user", "role": "student"}, expires_delta=timedelta(minutes=30)
    )
    response = client.post(
        "/admin/league-create",
        headers={"Authorization": f"Bearer {non_admin_token}"},
        json={"name": "non_admin_league", "game": "greedy_pig"},
    )
    assert response.status_code == 403


def test_update_expiry_success(client, auth_headers, db_session):
    """Test successful league expiry date updates"""

    # Create a test league
    league = League(
        name="expiry_test_league",
        game="greedy_pig",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=1),
    )
    db_session.add(league)
    db_session.commit()

    # Test case 1: Update expiry date to future date
    new_expiry = datetime.now() + timedelta(days=7)
    response = client.post(
        "/admin/update-expiry-date",
        headers=auth_headers,
        json={"league": "expiry_test_league", "date": new_expiry.isoformat()},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "updated successfully" in data["message"]

    # Verify expiry date was updated in database
    league = db_session.exec(
        select(League).where(League.name == "expiry_test_league")
    ).first()
    assert league.expiry_date > datetime.now() + timedelta(days=6)

    # Test case 2: Update expiry date for league with active teams
    # Add a team to the league
    team = Team(
        name="test_team",
        school_name="Test School",
        password_hash="hash",
        league_id=league.id,
    )
    db_session.add(team)
    db_session.commit()

    new_expiry = datetime.now() + timedelta(days=14)
    response = client.post(
        "/admin/update-expiry-date",
        headers=auth_headers,
        json={"league": "expiry_test_league", "date": new_expiry.isoformat()},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_update_expiry_exceptions(client, auth_headers, db_session):
    """Test error cases for updating league expiry date"""

    # Test case 1: Non-existent league
    new_expiry = datetime.now() + timedelta(days=7)
    response = client.post(
        "/admin/update-expiry-date",
        headers=auth_headers,
        json={"league": "non_existent_league", "date": new_expiry.isoformat()},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()

    # Test case 2: Past expiry date
    response = client.post(
        "/admin/update-expiry-date",
        headers=auth_headers,
        json={
            "league": "expiry_test_league",
            "date": (datetime.now() - timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 422

    # Test case 3: Invalid date format
    response = client.post(
        "/admin/update-expiry-date",
        headers=auth_headers,
        json={"league": "expiry_test_league", "date": "invalid-date"},
    )
    assert response.status_code == 422

    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/admin/update-expiry-date",
        json={"league": "expiry_test_league", "date": new_expiry.isoformat()},
    )
    assert response.status_code == 401


def test_get_league_results_success(client, auth_headers, db_session):
    """Test successful retrieval of league results"""

    # Create test league
    league = League(
        name="results_test_league",
        game="greedy_pig",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
    )
    db_session.add(league)
    db_session.commit()

    # Add some simulation results
    sim_result = SimulationResult(
        league_id=league.id,
        timestamp=datetime.now(),
        num_simulations=10,
        custom_rewards="[10, 8, 6, 4, 3, 2, 1]",
    )
    db_session.add(sim_result)
    db_session.commit()

    # Test case 1: Get results for league with simulations
    response = client.post(
        "/admin/get-all-league-results",
        headers=auth_headers,
        json={"name": "results_test_league"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data["data"]
    assert len(data["data"]["results"]) > 0

    # Test case 2: Get results for league without simulations
    # Create new league without simulations
    empty_league = League(
        name="empty_results_league",
        game="greedy_pig",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
    )
    db_session.add(empty_league)
    db_session.commit()

    response = client.post(
        "/admin/get-all-league-results",
        headers=auth_headers,
        json={"name": "empty_results_league"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data["data"]
    assert len(data["data"]["results"]) == 0


def test_get_league_results_exceptions(client, auth_headers):
    """Test error cases for getting league results"""

    # Test case 1: Non-existent league
    response = client.post(
        "/admin/get-all-league-results",
        headers=auth_headers,
        json={"name": "non_existent_league"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()

    # Test case 2: Empty league name
    response = client.post(
        "/admin/get-all-league-results", headers=auth_headers, json={"name": ""}
    )
    assert response.status_code == 422

    # Test case 3: Unauthorized access (no token)
    response = client.post(
        "/admin/get-all-league-results", json={"name": "test_league"}
    )
    assert response.status_code == 401

    # Test case 4: Non-admin token
    non_admin_token = create_access_token(
        data={"sub": "user", "role": "student"}, expires_delta=timedelta(minutes=30)
    )
    response = client.post(
        "/admin/get-all-league-results",
        headers={"Authorization": f"Bearer {non_admin_token}"},
        json={"name": "test_league"},
    )
    # Note: This endpoint allows any role, so it should succeed
    assert response.status_code == 200
