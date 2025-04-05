from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, League, Team
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def institution_with_teams(db_session: Session) -> tuple:
    """Setup institution with multiple teams for testing"""
    # Create an institution
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
    
    # Create a league for the teams
    league = League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
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
            institution_id=institution.id,
        )
        db_session.add(team)
        teams.append(team)
    db_session.commit()
    
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
    
    return institution, teams, token, headers


def test_get_all_teams_success(client, institution_with_teams, db_session):
    """Test successful retrieval of all teams"""
    institution, teams, _, headers = institution_with_teams
    
    # Get all teams
    response = client.get("/institution/get-all-teams", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "teams" in data["data"]
    
    # Verify all teams are returned
    teams_data = data["data"]["teams"]
    assert len(teams_data) == len(teams)
    
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


def test_get_all_teams_failures(client, institution_with_teams, db_session):
    """Test failure cases for getting all teams"""
    institution, _, _, _ = institution_with_teams
    
    # Test case 1: Unauthorized access (no token)
    response = client.get("/institution/get-all-teams")
    assert response.status_code == 401
    
    # Test case 2: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.get(
        "/institution/get-all-teams",
        headers={"Authorization": f"Bearer {wrong_token}"},
    )
    assert response.status_code == 403
    
    # Test case 3: Institution token without institution_id
    incomplete_token = create_access_token(
        data={"sub": institution.name, "role": "institution"},  # Missing institution_id
        expires_delta=timedelta(minutes=30),
    )
    response = client.get(
        "/institution/get-all-teams",
        headers={"Authorization": f"Bearer {incomplete_token}"},
    )
    assert response.status_code == 200  # API returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert "institution id" in data["message"].lower()
    
    # Test case 4: Expired token
    expired_token = create_access_token(
        data={
            "sub": institution.name,
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(microseconds=1),  # Immediate expiration
    )
    # Wait a bit to ensure token expiration
    import time
    time.sleep(0.01)
    response = client.get(
        "/institution/get-all-teams",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401