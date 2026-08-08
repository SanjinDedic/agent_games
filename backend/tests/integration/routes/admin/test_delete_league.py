from datetime import timedelta

import pytest
from sqlmodel import Session, select


from backend.database.db_models import UNASSIGNED_LEAGUE_NAME, League, Team
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def delete_league_setup(db_session: Session) -> tuple:
    """Setup and leagues for testing league deletion"""
    db_session.commit()
    
    # Create a league to delete
    league = League(
        name="league_to_delete",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
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
    )
    db_session.add(team)
    db_session.commit()
    
    # Create token
    token = create_access_token(
        data={
            "sub": "test_admin",
            "role": "admin",
        },
        expires_delta=timedelta(minutes=30),
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    return league, team, token, headers


def test_delete_league_success(client, delete_league_setup, db_session):
    """Test successful league deletion"""
    league, team, _, headers = delete_league_setup
    
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
        
    ).first()
    
    if not unassigned_league:
        # Create unassigned league for this test
        unassigned_league = League(
            name="unassigned",
            created_date=utc_now(),
            expiry_date=utc_now() + timedelta(days=365),
            game="greedy_pig",
        )
        db_session.add(unassigned_league)
        db_session.commit()
        db_session.refresh(unassigned_league)
    
    # Delete the league
    response = client.post(
        "/admin/delete-league",
        headers=headers,
        json={"league_id": league.id},
    )
    assert response.status_code == 200
    data = response.json()
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
    league, _, _, headers = delete_league_setup
    
    # Test case 1: Try to delete non-existent league
    response = client.post(
        "/admin/delete-league",
        headers=headers,
        json={"league_id": 99999},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    
    # Test case 2: Try to delete "unassigned" league
    # First make sure it exists
    unassigned_league = db_session.exec(
        select(League)
        .where(League.name == "unassigned")
        
    ).first()
    
    if not unassigned_league:
        # Create unassigned league for this test
        unassigned_league = League(
            name="unassigned",
            created_date=utc_now(),
            expiry_date=utc_now() + timedelta(days=365),
            game="greedy_pig",
        )
        db_session.add(unassigned_league)
        db_session.commit()
    
    response = client.post(
        "/admin/delete-league",
        headers=headers,
        json={"league_id": unassigned_league.id},
    )
    assert response.status_code == 400
    assert "cannot delete" in response.json()["detail"].lower()
    


def test_delete_league_requires_the_unassigned_league(client, admin_headers, db_session):
    """A missing 'unassigned' league is a broken install, not something to paper
    over. get_unassigned_league used to create one on demand; now it raises, so
    the failure points at init_db instead of silently minting a second
    definition of a load-bearing singleton.
    """
    league = League(
        name="league_to_delete_no_unassigned",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    league_id = league.id

    unassigned = db_session.exec(
        select(League).where(League.name == UNASSIGNED_LEAGUE_NAME)
    ).one()
    db_session.delete(unassigned)
    db_session.commit()

    response = client.post(
        "/admin/delete-league", headers=admin_headers, json={"league_id": league_id}
    )
    assert response.status_code == 404
    assert "init_db" in response.json()["detail"]


