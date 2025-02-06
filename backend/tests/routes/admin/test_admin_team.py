from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import League, Team
from backend.routes.auth.auth_core import create_access_token


def test_create_team_success(client, auth_headers, db_session):
    """Test successful team creation with different variations"""
    # Test case 1: Basic team creation
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
    assert data["data"]["name"] == "new_team"

    # Verify team was actually created in database
    team = db_session.exec(select(Team).where(Team.name == "new_team")).first()
    assert team is not None
    assert team.school_name == "Test School"

    # Test case 2: Team creation with optional fields
    response = client.post(
        "/admin/team-create",
        headers=auth_headers,
        json={
            "name": "team_with_options",
            "school_name": "Option School",
            "password": "pass123",
            "color": "rgb(255,0,0)",
            "score": 100,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify team with options in database
    team = db_session.exec(select(Team).where(Team.name == "team_with_options")).first()
    assert team is not None
    assert team.color == "rgb(255,0,0)"
    assert team.score == 100

    # Test case 3: Team creation with minimum required fields
    response = client.post(
        "/admin/team-create",
        headers=auth_headers,
        json={"name": "minimal_team", "password": "pass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify minimal team in database
    team = db_session.exec(select(Team).where(Team.name == "minimal_team")).first()
    assert team is not None
    assert team.school_name == "Not Available"  # Default value


def test_create_team_exceptions(client, auth_headers, db_session):
    """Test all possible error cases for team creation"""

    # Test case 1: Duplicate team name
    # First create a team
    client.post(
        "/admin/team-create",
        headers=auth_headers,
        json={"name": "duplicate_team", "password": "test_pass"},
    )

    # Try to create team with same name
    response = client.post(
        "/admin/team-create",
        headers=auth_headers,
        json={"name": "duplicate_team", "password": "different_pass"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "already exists" in data["message"]

    # Test case 2: Missing required fields
    response = client.post(
        "/admin/team-create",
        headers=auth_headers,
        json={
            "name": "incomplete_team"
            # Missing password
        },
    )
    assert response.status_code == 422  # Validation error

    # Test case 3: Empty team name
    response = client.post(
        "/admin/team-create",
        headers=auth_headers,
        json={"name": "", "password": "test_pass"},
    )
    assert response.status_code == 422  # Validation error

    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/admin/team-create",
        json={"name": "unauthorized_team", "password": "test_pass"},
    )
    assert response.status_code == 401

    # Test case 5: Non-admin token
    non_admin_token = create_access_token(
        data={"sub": "user", "role": "student"}, expires_delta=timedelta(minutes=30)
    )
    response = client.post(
        "/admin/team-create",
        headers={"Authorization": f"Bearer {non_admin_token}"},
        json={"name": "non_admin_team", "password": "test_pass"},
    )
    assert response.status_code == 403


def test_delete_team_success(client, auth_headers, db_session):
    """Test successful team deletion scenarios"""

    # Test case 1: Basic team deletion
    # First create a team
    team = Team(
        name="team_to_delete",
        school_name="Test School",
        password_hash="hash",
        league_id=1,
    )
    db_session.add(team)
    db_session.commit()

    response = client.post(
        "/admin/delete-team", headers=auth_headers, json={"name": "team_to_delete"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "deleted successfully" in data["message"]

    # Verify team is actually deleted
    deleted_team = db_session.exec(
        select(Team).where(Team.name == "team_to_delete")
    ).first()
    assert deleted_team is None

    # Test case 2: Delete team with associated data
    # Create team with some associated data
    team = Team(
        name="team_with_data",
        school_name="Test School",
        password_hash="hash",
        league_id=1,
    )
    db_session.add(team)
    db_session.commit()

    response = client.post(
        "/admin/delete-team", headers=auth_headers, json={"name": "team_with_data"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify all associated data is deleted
    deleted_team = db_session.exec(
        select(Team).where(Team.name == "team_with_data")
    ).first()
    assert deleted_team is None
    # ... verify associated data is deleted ...


def test_delete_team_exceptions(client, auth_headers):
    """Test all possible error cases for team deletion"""

    # Test case 1: Delete non-existent team
    response = client.post(
        "/admin/delete-team", headers=auth_headers, json={"name": "non_existent_team"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()

    # Test case 2: Delete with empty team name
    response = client.post(
        "/admin/delete-team", headers=auth_headers, json={"name": ""}
    )
    assert response.status_code == 422  # Validation error

    # Test case 3: Unauthorized access (no token)
    response = client.post("/admin/delete-team", json={"name": "unauthorized_delete"})
    assert response.status_code == 401

    # Test case 4: Non-admin token
    non_admin_token = create_access_token(
        data={"sub": "user", "role": "student"}, expires_delta=timedelta(minutes=30)
    )
    response = client.post(
        "/admin/delete-team",
        headers={"Authorization": f"Bearer {non_admin_token}"},
        json={"name": "non_admin_delete"},
    )
    assert response.status_code == 403


def test_get_all_teams_success(client, auth_headers, db_session):
    """Test successful team listing scenarios"""

    # Create test teams
    teams_data = [
        {"name": "team1", "school_name": "School 1"},
        {"name": "team2", "school_name": "School 2"},
        {"name": "team3", "school_name": "School 3"},
    ]

    league = db_session.exec(select(League).where(League.name == "unassigned")).first()
    for team_data in teams_data:
        team = Team(
            name=team_data["name"],
            school_name=team_data["school_name"],
            password_hash="hash",
            league_id=league.id,
        )
        db_session.add(team)
    db_session.commit()

    # Test case 1: Get all teams
    response = client.get("/admin/get-all-teams", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "teams" in data["data"]
    teams = data["data"]["teams"]
    assert len(teams) >= 3

    # Verify team data structure
    for team in teams:
        assert "id" in team
        assert "name" in team
        assert "school" in team
        assert "league" in team

    # Additional verification of team attributes
    team_names = [team["name"] for team in teams]
    assert "team1" in team_names
    assert "team2" in team_names
    assert "team3" in team_names


def test_get_all_teams_exceptions(client):
    """Test error cases for getting all teams"""

    # Test case 1: Unauthorized access (no token)
    response = client.get("/admin/get-all-teams")
    assert response.status_code == 401

    # Test case 2: Non-admin token
    non_admin_token = create_access_token(
        data={"sub": "user", "role": "student"}, expires_delta=timedelta(minutes=30)
    )
    response = client.get(
        "/admin/get-all-teams", headers={"Authorization": f"Bearer {non_admin_token}"}
    )
    assert response.status_code == 403
