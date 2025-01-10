import json
from datetime import datetime, timedelta

import pytest
from database.db_models import League, Team
from fastapi.testclient import TestClient
from sqlmodel import Session, select


def test_create_league_success(client: TestClient, auth_headers: dict):
    """Test successful league creation"""
    response = client.post(
        "/admin/league_create",
        headers=auth_headers,
        json={"name": "new_league", "game": "greedy_pig"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "league_id" in data["data"]


def test_create_league_unauthorized(client: TestClient):
    """Test league creation without admin authorization"""
    response = client.post(
        "/admin/league_create", json={"name": "new_league", "game": "greedy_pig"}
    )
    assert response.status_code == 401


def test_create_league_invalid_game(client: TestClient, auth_headers: dict):
    """Test league creation with invalid game"""
    response = client.post(
        "/admin/league_create",
        headers=auth_headers,
        json={"name": "new_league", "game": "invalid_game"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["type"] == "value_error"
    assert (
        data["detail"][0]["msg"]
        == "Value error, Game must be one of: prisoners_dilemma, greedy_pig"
    )


def test_create_team_success(client: TestClient, auth_headers: dict):
    """Test successful team creation"""
    response = client.post(
        "/admin/team_create",
        headers=auth_headers,
        json={
            "name": "new_team",
            "school_name": "Test School",
            "password": "test_password",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "team_id" in data["data"]


def test_create_team_duplicate(client: TestClient, auth_headers: dict):
    """Test creating a team with duplicate name"""
    # Create first team
    client.post(
        "/admin/team_create",
        headers=auth_headers,
        json={
            "name": "duplicate_team",
            "school_name": "Test School",
            "password": "test_password",
        },
    )

    # Try to create duplicate
    response = client.post(
        "/admin/team_create",
        headers=auth_headers,
        json={
            "name": "duplicate_team",
            "school_name": "Test School",
            "password": "test_password",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "already exists" in data["message"]


def test_get_all_admin_leagues(
    client: TestClient, auth_headers: dict, test_league: League
):
    """Test retrieving all admin leagues"""
    response = client.get("/admin/get_all_admin_leagues", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]["leagues"]) >= 1
    assert any(league["name"] == test_league.name for league in data["data"]["leagues"])


def test_delete_team_success(
    client: TestClient, auth_headers: dict, db_session: Session
):
    """Test successful team deletion"""
    # Create a team to delete
    team = Team(
        name="team_to_delete",
        school_name="Test School",
        password_hash="hash",
        league_id=1,  # Add league_id
    )
    db_session.add(team)
    db_session.commit()

    response = client.post(
        "/admin/delete_team",
        headers=auth_headers,
        json={"name": "team_to_delete"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    # Verify team is deleted from database
    deleted_team = db_session.exec(
        select(Team).where(Team.name == "team_to_delete")
    ).first()
    assert deleted_team is None, "Team was not deleted from database"


def test_get_all_teams(client: TestClient, auth_headers: dict, db_session: Session):
    """Test retrieving all teams"""
    # Create some test teams
    teams = [
        Team(
            name=f"team_{i}",
            school_name="Test School",
            password_hash="hash",
            league_id=1,
        )
        for i in range(3)
    ]
    for team in teams:
        db_session.add(team)
    db_session.commit()

    response = client.get("/admin/get_all_teams", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]["teams"]) >= 3


def test_update_expiry_date(
    client: TestClient, auth_headers: dict, test_league: League
):
    """Test updating league expiry date"""
    new_expiry = datetime.now() + timedelta(days=7)
    response = client.post(
        "/admin/update_expiry_date",
        headers=auth_headers,
        json={"league": test_league.name, "date": new_expiry.isoformat()},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "updated successfully" in data["message"]


def test_get_league_results(
    client: TestClient, auth_headers: dict, test_league: League
):
    """Test retrieving league results"""
    response = client.post(
        "/admin/get_all_league_results",
        headers=auth_headers,
        json={"name": test_league.name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data["data"]
