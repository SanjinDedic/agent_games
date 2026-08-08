from datetime import timedelta

import pytest
from sqlmodel import Session

from backend.database.db_models import League, Team
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def assignment_setup(db_session: Session) -> tuple:
    """Two leagues and a team sitting in the first of them."""
    league1 = League(
        name="source_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    league2 = League(
        name="target_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="prisoners_dilemma",
    )
    db_session.add(league1)
    db_session.add(league2)
    db_session.commit()
    db_session.refresh(league1)
    db_session.refresh(league2)

    team = Team(
        name="team_to_assign",
        school_name="Test School",
        password_hash="test_hash",
        league_id=league1.id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    return league1, league2, team


def test_assign_team_to_league_success(client, assignment_setup, owner_headers, db_session):
    """Test successful team assignment to a league"""
    source_league, target_league, team = assignment_setup

    # Verify team is initially in source league
    assert team.league_id == source_league.id

    # Assign team to target league
    response = client.post(
        "/owner/assign-team-to-league",
        headers=owner_headers,
        json={"team_id": team.id, "league_id": target_league.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert f"Team '{team.name}' assigned to league '{target_league.name}'" in data["message"]

    # Verify team was moved to target league
    db_session.refresh(team)
    assert team.league_id == target_league.id

    # Move team back to source league
    response = client.post(
        "/owner/assign-team-to-league",
        headers=owner_headers,
        json={"team_id": team.id, "league_id": source_league.id},
    )
    assert response.status_code == 200

    # Verify team was moved back
    db_session.refresh(team)
    assert team.league_id == source_league.id


def test_assign_team_to_league_failures(client, assignment_setup, owner_headers):
    """Test failure cases for team assignment"""
    _, target_league, team = assignment_setup

    # Test case 1: Non-existent team
    response = client.post(
        "/owner/assign-team-to-league",
        headers=owner_headers,
        json={"team_id": 99999, "league_id": target_league.id},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # Test case 2: Non-existent league
    response = client.post(
        "/owner/assign-team-to-league",
        headers=owner_headers,
        json={"team_id": team.id, "league_id": 99999},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # Test case 3: Unauthorized access (no token)
    response = client.post(
        "/owner/assign-team-to-league",
        json={"team_id": team.id, "league_id": target_league.id},
    )
    assert response.status_code == 401

    # Test case 4: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/owner/assign-team-to-league",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={"team_id": team.id, "league_id": target_league.id},
    )
    assert response.status_code == 403
