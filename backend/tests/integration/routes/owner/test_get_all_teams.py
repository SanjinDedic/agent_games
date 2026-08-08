from datetime import timedelta

import pytest
from sqlmodel import Session, select


from backend.database.db_models import League, Team
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def teams_setup(db_session: Session) -> tuple:
    """Setup with multiple teams for testing"""
    db_session.commit()
    
    # Create a league for the teams
    league = League(
        name="test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()
    
    # Create multiple teams
    teams = []
    for i in range(3):
        team = Team(
            name=f"test_team_{i}",
            school_name=f"School {i}",
            password_hash="test_hash",
            league_id=league.id,
        )
        db_session.add(team)
        teams.append(team)
    db_session.commit()
    
    # Create token
    token = create_access_token(
        data={
            "sub": "test_owner",
            "role": "owner",
        },
        expires_delta=timedelta(minutes=30),
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    return teams, token, headers


def test_get_all_teams_success(client, teams_setup, db_session):
    """Test successful retrieval of all teams"""
    teams, _, headers = teams_setup
    
    # Get all teams
    response = client.get("/owner/get-all-teams", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "teams" in data

    # Every team in the deployment is returned, so the fixture's teams are a
    # subset of the response rather than all of it.
    teams_data = data["teams"]
    assert len(teams_data) >= len(teams)
    
    # Check team names are present
    team_names = [team["name"] for team in teams_data]
    for i in range(3):
        assert f"test_team_{i}" in team_names
    
    # Check team data structure
    for team in teams_data:
        assert "id" in team
        assert "name" in team
        assert "school" in team
        assert "league" in team


def test_get_all_teams_failures(client, teams_setup, db_session):
    """Test failure cases for getting all teams"""
    _, _, _ = teams_setup
    
    # Test case 1: Unauthorized access (no token)
    response = client.get("/owner/get-all-teams")
    assert response.status_code == 401
    
    # Test case 2: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.get(
        "/owner/get-all-teams",
        headers={"Authorization": f"Bearer {wrong_token}"},
    )
    assert response.status_code == 403
    
    
    # Test case 4: Expired token
    expired_token = create_access_token(
        data={
            "sub": "test_owner",
            "role": "owner",
        },
        expires_delta=timedelta(microseconds=1),  # Immediate expiration
    )
    # Wait a bit to ensure token expiration
    import time
    time.sleep(0.01)
    response = client.get(
        "/owner/get-all-teams",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401