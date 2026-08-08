"""Tests for unassign-team and get_unassigned_league — covering previously uncovered paths."""

from datetime import timedelta

import pytest
from sqlmodel import Session, select


from backend.database.db_models import UNASSIGNED_LEAGUE_NAME, League, LeagueType, Team, TeamType
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def unassign_setup(db_session: Session) -> dict:
    """A league and a team, for unassign tests."""
    now = utc_now()

    unassigned = db_session.exec(
        select(League).where(League.name == UNASSIGNED_LEAGUE_NAME)
    ).one()

    league = League(
        name="unassign_test_league",
        created_date=now,
        expiry_date=now + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    team = Team(
        name="unassign_test_team",
        school_name="School",
        password_hash="hash",
        league_id=league.id,
        team_type=TeamType.STUDENT,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    token = create_access_token(
        data={"sub": "test_owner", "role": "owner"},
        expires_delta=timedelta(minutes=30),
    )

    return {
        "league": league,
        "unassigned": unassigned,
        "team": team,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def test_unassign_team_success(client, unassign_setup, db_session):
    """Unassign moves team to the unassigned league."""
    data = unassign_setup

    resp = client.post(
        "/owner/unassign-team",
        headers=data["headers"],
        json={"team_id": data["team"].id},
    )
    assert resp.status_code == 200
    assert "unassigned" in resp.json()["message"].lower()

    # Verify in DB
    db_session.refresh(data["team"])
    assert data["team"].league_id == data["unassigned"].id


def test_unassign_team_not_found(client, unassign_setup):
    """Unassign non-existent team returns error."""
    resp = client.post(
        "/owner/unassign-team",
        headers=unassign_setup["headers"],
        json={"team_id": 99999},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

