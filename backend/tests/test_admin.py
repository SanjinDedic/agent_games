import json
from datetime import datetime, timedelta

import pytest
from database.db_models import Admin, League, Team
from fastapi.testclient import TestClient
from sqlmodel import Session, select


def print_db_state(session: Session):
    """Helper function to print current database state"""
    # Print all leagues
    leagues = session.exec(select(League)).all()
    print("\nLeagues:")
    for league in leagues:
        print(f"  ID: {league.id}, Name: {league.name}, Game: {league.game}")

    # Print all teams
    teams = session.exec(select(Team)).all()
    print("\nTeams:")
    for team in teams:
        print(
            f"  ID: {team.id}, Name: {team.name}, League ID: {team.league_id}, School: {team.school_name}"
        )

    # Print all admins
    admins = session.exec(select(Admin)).all()
    print("\nAdmins:")
    for admin in admins:
        print(f"  ID: {admin.id}, Username: {admin.username}")

    # Print separator for readability
    print("\n" + "=" * 80)


def test_create_league_success(client: TestClient, auth_headers: dict):
    """Test successful league creation"""
    response = client.post(
        "/admin/league-create",
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
        "/admin/league-create", json={"name": "new_league", "game": "greedy_pig"}
    )
    assert response.status_code == 401


def test_create_league_invalid_game(client: TestClient, auth_headers: dict):
    """Test league creation with invalid game"""
    response = client.post(
        "/admin/league-create",
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
        "/admin/team-create",
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
        "/admin/team-create",
        headers=auth_headers,
        json={
            "name": "duplicate_team",
            "school_name": "Test School",
            "password": "test_password",
        },
    )

    # Try to create duplicate
    response = client.post(
        "/admin/team-create",
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
    response = client.get("/user/get-all-leagues", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]["leagues"]) >= 1
    assert any(league["name"] == test_league.name for league in data["data"]["leagues"])


def test_delete_team_success(
    client: TestClient, auth_headers: dict, db_session: Session
):
    """Test successful team deletion"""
    # Print initial database state
    print("\nInitial Database State:")
    print_db_state(db_session)

    # Create a team to delete
    team = Team(
        name="team_to_delete",
        school_name="Test School",
        password_hash="hash",
        league_id=1,  # Add league_id
    )
    db_session.add(team)
    db_session.commit()

    print("\nDatabase State After Team Creation:")
    print_db_state(db_session)

    response = client.post(
        "/admin/delete-team",
        headers=auth_headers,
        json={"name": "team_to_delete"},
    )

    print("\nAPI Response:", response.json())

    print("\nDatabase State After Delete Request:")
    print_db_state(db_session)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify team is deleted from database
    deleted_team = db_session.exec(
        select(Team).where(Team.name == "team_to_delete")
    ).first()

    if deleted_team is not None:
        print("\nTeam that should be deleted but still exists:")
        print(f"Team ID: {deleted_team.id}")
        print(f"Team Name: {deleted_team.name}")
        print(f"League ID: {deleted_team.league_id}")
        print(f"School Name: {deleted_team.school_name}")

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

    response = client.get("/admin/get-all-teams", headers=auth_headers)
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
        "/admin/update-expiry-date",
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
        "/admin/get-all-league-results",
        headers=auth_headers,
        json={"name": test_league.name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data["data"]
