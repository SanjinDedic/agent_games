from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, League, Team
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def assignment_setup(db_session: Session) -> tuple:
    """Setup institution, leagues, and team for testing team assignment"""
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
    
    # Create two leagues
    league1 = League(
        name="source_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    league2 = League(
        name="target_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="prisoners_dilemma",
        institution_id=institution.id,
    )
    db_session.add(league1)
    db_session.add(league2)
    db_session.commit()
    db_session.refresh(league1)
    db_session.refresh(league2)
    
    # Create a team in the source league
    team = Team(
        name="team_to_assign",
        school_name="Test School",
        password_hash="test_hash",
        league_id=league1.id,
        institution_id=institution.id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    
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
    
    return institution, league1, league2, team, token, headers


def test_assign_team_to_league_success(client, assignment_setup, db_session):
    """Test successful team assignment to a league"""
    institution, source_league, target_league, team, _, headers = assignment_setup
    
    # Verify team is initially in source league
    assert team.league_id == source_league.id
    
    # Assign team to target league
    response = client.post(
        "/institution/assign-team-to-league",
        headers=headers,
        json={"team_id": team.id, "league_id": target_league.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert f"Team '{team.name}' assigned to league '{target_league.name}'" in data["message"]
    
    # Verify team was moved to target league
    db_session.refresh(team)
    assert team.league_id == target_league.id
    
    # Move team back to source league
    response = client.post(
        "/institution/assign-team-to-league",
        headers=headers,
        json={"team_id": team.id, "league_id": source_league.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    # Verify team was moved back
    db_session.refresh(team)
    assert team.league_id == source_league.id


def test_assign_team_to_league_failures(client, assignment_setup, db_session):
    """Test failure cases for team assignment"""
    institution, source_league, target_league, team, _, headers = assignment_setup
    
    # Test case 1: Non-existent team
    response = client.post(
        "/institution/assign-team-to-league",
        headers=headers,
        json={"team_id": 99999, "league_id": target_league.id},
    )
    assert response.status_code == 200  # API returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    
    # Test case 2: Non-existent league
    response = client.post(
        "/institution/assign-team-to-league",
        headers=headers,
        json={"team_id": team.id, "league_id": 99999},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    
    # Test case 3: Team from different institution
    # Create another institution, league, and team
    other_institution = Institution(
        name="other_institution",
        contact_person="Other Person",
        contact_email="other@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="test_hash",
    )
    db_session.add(other_institution)
    db_session.commit()
    
    other_league = League(
        name="other_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=other_institution.id,
    )
    db_session.add(other_league)
    db_session.commit()
    
    other_team = Team(
        name="other_team",
        school_name="Other School",
        password_hash="test_hash",
        league_id=other_league.id,
        institution_id=other_institution.id,
    )
    db_session.add(other_team)
    db_session.commit()
    
    # Try to assign team from other institution
    response = client.post(
        "/institution/assign-team-to-league",
        headers=headers,
        json={"team_id": other_team.id, "league_id": target_league.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "permission" in data["message"].lower()
    
    # Test case 4: League from different institution
    response = client.post(
        "/institution/assign-team-to-league",
        headers=headers,
        json={"team_id": team.id, "league_id": other_league.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "permission" in data["message"].lower()
    
    # Test case 5: Unauthorized access (no token)
    response = client.post(
        "/institution/assign-team-to-league",
        json={"team_id": team.id, "league_id": target_league.id},
    )
    assert response.status_code == 401
    
    # Test case 6: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/institution/assign-team-to-league",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={"team_id": team.id, "league_id": target_league.id},
    )
    assert response.status_code == 403