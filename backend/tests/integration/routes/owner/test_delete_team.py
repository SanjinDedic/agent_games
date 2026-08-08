from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.tests.conftest import add_submission
from backend.database.db_models import (League, Submission,
                                        SubmissionMetadata, Team)
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def owner_setup(db_session: Session) -> tuple:
    """Setup for testing and return necessary objects"""
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
    
    # Create a team to delete
    team = Team(
        name="team_to_delete",
        school_name="Test School",
        password_hash="test_hash",
        league_id=league.id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    
    # Add a submission for the team
    add_submission(
        db_session,
        code="test code",
        timestamp=utc_now(),
        team_id=team.id,
    )
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
    
    return team, token, headers


def test_delete_team_success(client, owner_setup, db_session):
    """Test successful team deletion"""
    team, _, headers = owner_setup
    
    # Verify team exists before deletion
    existing_team = db_session.exec(
        select(Team).where(Team.id == team.id)
    ).first()
    assert existing_team is not None
    
    # Delete the team
    response = client.post(
        "/owner/delete-team",
        headers=headers,
        json={"id": team.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert "deleted successfully" in data["message"]
    
    # Verify team was actually deleted
    deleted_team = db_session.exec(
        select(Team).where(Team.id == team.id)
    ).first()
    assert deleted_team is None
    
    # Verify submissions were deleted (metadata and code rows)
    attempts = db_session.exec(
        select(SubmissionMetadata).where(SubmissionMetadata.team_id == team.id)
    ).all()
    assert len(attempts) == 0
    orphaned_code = db_session.exec(
        select(Submission).where(
            ~Submission.metadata_id.in_(select(SubmissionMetadata.id))
        )
    ).all()
    assert len(orphaned_code) == 0


def test_delete_team_failures(client, owner_setup, db_session):
    """Test failure cases for team deletion"""
    team, _, headers = owner_setup
    
    # Test case 1: Delete non-existent team
    response = client.post(
        "/owner/delete-team",
        headers=headers,
        json={"id": 9999999},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    
    
    # Test case 3: Invalid team ID format
    response = client.post(
        "/owner/delete-team",
        headers=headers,
        json={"id": "invalid_id"},
    )
    assert response.status_code == 422
    
    # Test case 4: Unauthorized access (no token)
    response = client.post(
        "/owner/delete-team",
        json={"id": team.id},
    )
    assert response.status_code == 401