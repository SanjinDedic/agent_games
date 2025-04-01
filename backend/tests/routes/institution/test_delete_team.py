from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, League, Submission, Team
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def institution_setup(db_session: Session) -> tuple:
    """Setup institution with teams for testing and return necessary objects"""
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
    
    # Create a team to delete
    team = Team(
        name="team_to_delete",
        school_name="Test School",
        password_hash="test_hash",
        league_id=league.id,
        institution_id=institution.id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    
    # Add a submission for the team
    submission = Submission(
        code="test code",
        timestamp=datetime.now(),
        team_id=team.id,
    )
    db_session.add(submission)
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
    
    return institution, team, token, headers


def test_delete_team_success(client, institution_setup, db_session):
    """Test successful team deletion"""
    _, team, _, headers = institution_setup
    
    # Verify team exists before deletion
    existing_team = db_session.exec(
        select(Team).where(Team.id == team.id)
    ).first()
    assert existing_team is not None
    
    # Delete the team
    response = client.post(
        "/institution/delete-team",
        headers=headers,
        json={"id": team.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "deleted successfully" in data["message"]
    
    # Verify team was actually deleted
    deleted_team = db_session.exec(
        select(Team).where(Team.id == team.id)
    ).first()
    assert deleted_team is None
    
    # Verify submissions were deleted
    submissions = db_session.exec(
        select(Submission).where(Submission.team_id == team.id)
    ).all()
    assert len(submissions) == 0


def test_delete_team_failures(client, institution_setup, db_session):
    """Test failure cases for team deletion"""
    institution, team, _, headers = institution_setup
    
    # Test case 1: Delete non-existent team
    response = client.post(
        "/institution/delete-team",
        headers=headers,
        json={"id": 9999999},
    )
    assert response.status_code == 200  # API returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    
    # Test case 2: Delete team from different institution
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
    
    # Try to delete a team from the first institution
    response = client.post(
        "/institution/delete-team",
        headers=other_headers,
        json={"id": team.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "permission" in data["message"].lower()
    
    # Test case 3: Invalid team ID format
    response = client.post(
        "/institution/delete-team",
        headers=headers,
        json={"id": "invalid_id"},
    )
    assert response.status_code == 422
    
    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/institution/delete-team",
        json={"id": team.id},
    )
    assert response.status_code == 401