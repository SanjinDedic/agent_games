from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, League, Team
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def delete_league_setup(db_session: Session) -> tuple:
    """Setup institution and leagues for testing league deletion"""
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
    
    # Create a league to delete
    league = League(
        name="league_to_delete",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    
    # Add a team to the league
    team = Team(
        name="team_in_league",
        school_name="Test School",
        password_hash="test_hash",
        league_id=league.id,
        institution_id=institution.id,
    )
    db_session.add(team)
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
    
    return institution, league, team, token, headers


def test_delete_league_success(client, delete_league_setup, db_session):
    """Test successful league deletion"""
    institution, league, team, _, headers = delete_league_setup
    
    # Verify league and team exist before deletion
    existing_league = db_session.exec(
        select(League).where(League.id == league.id)
    ).first()
    assert existing_league is not None
    
    existing_team = db_session.exec(
        select(Team).where(Team.id == team.id)
    ).first()
    assert existing_team is not None
    assert existing_team.league_id == league.id
    
    # Verify "unassigned" league exists or will be created
    unassigned_league = db_session.exec(
        select(League)
        .where(League.name == "unassigned")
        .where(League.institution_id == institution.id)
    ).first()
    
    if not unassigned_league:
        # Create unassigned league for this test
        unassigned_league = League(
            name="unassigned",
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=365),
            game="greedy_pig",
            institution_id=institution.id,
        )
        db_session.add(unassigned_league)
        db_session.commit()
        db_session.refresh(unassigned_league)
    
    # Delete the league
    response = client.post(
        "/institution/delete-league",
        headers=headers,
        json={"name": league.name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "deleted" in data["message"]
    assert "moved to the unassigned league" in data["message"]
    
    # Verify league was deleted
    deleted_league = db_session.exec(
        select(League).where(League.id == league.id)
    ).first()
    assert deleted_league is None
    
    # Verify team was moved to unassigned league
    moved_team = db_session.exec(
        select(Team).where(Team.id == team.id)
    ).first()
    assert moved_team is not None
    assert moved_team.league_id == unassigned_league.id


def test_delete_league_failures(client, delete_league_setup, db_session):
    """Test failure cases for league deletion"""
    institution, league, _, _, headers = delete_league_setup
    
    # Test case 1: Try to delete non-existent league
    response = client.post(
        "/institution/delete-league",
        headers=headers,
        json={"name": "non_existent_league"},
    )
    assert response.status_code == 200  # API returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    
    # Test case 2: Try to delete "unassigned" league
    # First make sure it exists
    unassigned_league = db_session.exec(
        select(League)
        .where(League.name == "unassigned")
        .where(League.institution_id == institution.id)
    ).first()
    
    if not unassigned_league:
        # Create unassigned league for this test
        unassigned_league = League(
            name="unassigned",
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=365),
            game="greedy_pig",
            institution_id=institution.id,
        )
        db_session.add(unassigned_league)
        db_session.commit()
    
    response = client.post(
        "/institution/delete-league",
        headers=headers,
        json={"name": "unassigned"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "cannot delete" in data["message"].lower()
    
    # Test case 3: Try to delete league from different institution
    # Create another institution
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
    
    # Create token for other institution
    other_token = create_access_token(
        data={
            "sub": other_institution.name,
            "role": "institution",
            "institution_id": other_institution.id,
        },
        expires_delta=timedelta(minutes=30),
    )
    other_headers = {"Authorization": f"Bearer {other_token}"}
    
    # Try to delete league from first institution using other institution's token
    response = client.post(
        "/institution/delete-league",
        headers=other_headers,
        json={"name": league.name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    
    # Test case 4: Invalid league name format
    response = client.post(
        "/institution/delete-league",
        headers=headers,
        json={"name": ""},
    )
    assert response.status_code == 422
    
    # Test case 5: Unauthorized access (no token)
    response = client.post(
        "/institution/delete-league",
        json={"name": league.name},
    )
    assert response.status_code == 401
    
    # Test case 6: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/institution/delete-league",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={"name": league.name},
    )
    assert response.status_code == 403