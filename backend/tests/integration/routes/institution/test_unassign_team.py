"""Tests for unassign-team and get_unassigned_league — covering previously uncovered paths."""

from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, League, LeagueType, Team, TeamType
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def unassign_setup(db_session: Session) -> dict:
    """Create institution with a league, unassigned league, and a team."""
    now = datetime.now()

    institution = Institution(
        name="unassign_test_inst",
        contact_person="Test",
        contact_email="test@test.com",
        created_date=now,
        subscription_active=True,
        subscription_expiry=now + timedelta(days=30),
        docker_access=True,
        password_hash="hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    unassigned = League(
        name="unassigned",
        created_date=now,
        expiry_date=now + timedelta(days=365),
        game="greedy_pig",
        institution_id=institution.id,
        league_type=LeagueType.INSTITUTION,
    )
    db_session.add(unassigned)
    db_session.commit()
    db_session.refresh(unassigned)

    league = League(
        name="unassign_test_league",
        created_date=now,
        expiry_date=now + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    team = Team(
        name="unassign_test_team",
        school_name="School",
        password_hash="hash",
        league_id=league.id,
        institution_id=institution.id,
        team_type=TeamType.STUDENT,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    token = create_access_token(
        data={"sub": institution.name, "role": "institution", "institution_id": institution.id},
        expires_delta=timedelta(minutes=30),
    )

    return {
        "institution": institution,
        "league": league,
        "unassigned": unassigned,
        "team": team,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def test_unassign_team_success(client, unassign_setup, db_session):
    """Unassign moves team to the unassigned league."""
    data = unassign_setup

    resp = client.post(
        "/institution/unassign-team",
        headers=data["headers"],
        json={"team_id": data["team"].id},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert "unassigned" in resp.json()["message"].lower()

    # Verify in DB
    db_session.refresh(data["team"])
    assert data["team"].league_id == data["unassigned"].id


def test_unassign_team_not_found(client, unassign_setup):
    """Unassign non-existent team returns error."""
    resp = client.post(
        "/institution/unassign-team",
        headers=unassign_setup["headers"],
        json={"team_id": 99999},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


def test_unassign_team_wrong_institution(client, unassign_setup, db_session):
    """Cannot unassign a team from another institution."""
    other_inst = Institution(
        name="other_unassign_inst",
        contact_person="Other",
        contact_email="other@test.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="hash",
    )
    db_session.add(other_inst)
    db_session.commit()
    db_session.refresh(other_inst)

    other_token = create_access_token(
        data={"sub": other_inst.name, "role": "institution", "institution_id": other_inst.id},
        expires_delta=timedelta(minutes=30),
    )

    resp = client.post(
        "/institution/unassign-team",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"team_id": unassign_setup["team"].id},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"
