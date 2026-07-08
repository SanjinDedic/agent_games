"""Tests for the new endpoints/functions added on this branch:
- get_team_submission_history (user_db.py)
- GET /user/get-team-submissions (user_router.py)
"""

from datetime import timedelta

import pytest
from sqlmodel import Session, delete, select

from backend.tests.conftest import add_submission, build_institution
from backend.database.db_models import Institution, League, Team
from backend.database.submission_helpers import delete_submissions_for_teams
from backend.routes.auth.auth_core import create_access_token
from backend.routes.user.user_db import get_team_submission_history
from backend.tests.conftest import make_student_token
from backend.time_utils import utc_now


@pytest.fixture
def institution(db_session: Session) -> Institution:
    inst = db_session.exec(
        select(Institution).where(Institution.name == "Team Info Institution")
    ).first()
    if not inst:
        inst = build_institution(
            name="Team Info Institution",
            contact_person="Tester",
            contact_email="ti@example.com",
            created_date=utc_now(),
            subscription_expiry=utc_now() + timedelta(days=30),
            password_hash="hash",
        )
        db_session.add(inst)
        db_session.commit()
        db_session.refresh(inst)
    return inst


@pytest.fixture
def league_with_institution(db_session: Session, institution: Institution) -> League:
    league = db_session.exec(
        select(League).where(League.name == "team_info_league")
    ).first()
    if not league:
        league = League(
            name="team_info_league",
            game="prisoners_dilemma",
            created_date=utc_now(),
            expiry_date=utc_now() + timedelta(days=7),
            institution_id=institution.id,
        )
        db_session.add(league)
        db_session.commit()
        db_session.refresh(league)
    return league


@pytest.fixture
def team(db_session: Session, league_with_institution: League) -> Team:
    team = db_session.exec(select(Team).where(Team.name == "team_info_team")).first()
    if not team:
        team = Team(
            name="team_info_team",
            school_name="Test School",
            password_hash="hash",
            league_id=league_with_institution.id,
        )
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)
    return team


@pytest.fixture
def team_token(team: Team) -> str:
    return make_student_token(team)


# ---------------------------------------------------------------------------
# get_team_submission_history (DB function)
# ---------------------------------------------------------------------------


def test_get_team_submission_history_returns_newest_first(
    db_session: Session, team: Team
):
    delete_submissions_for_teams(db_session, [team.id])
    db_session.commit()

    base = utc_now()
    add_submission(db_session, code="old", timestamp=base, team_id=team.id, duration_ms=12.0)
    add_submission(
        db_session,
        code="newer",
        timestamp=base + timedelta(minutes=1),
        team_id=team.id,
        duration_ms=34.5,
    )
    add_submission(
        db_session,
        code="newest",
        timestamp=base + timedelta(minutes=2),
        team_id=team.id,
    )
    db_session.commit()

    history = get_team_submission_history(db_session, team.id)
    assert len(history) == 3
    assert [h["code"] for h in history] == ["newest", "newer", "old"]
    # Field shape
    for item in history:
        assert set(item.keys()) == {"id", "code", "timestamp", "duration_ms"}
    assert history[2]["duration_ms"] == 12.0
    assert history[0]["duration_ms"] is None


def test_get_team_submission_history_no_team(db_session: Session):
    assert get_team_submission_history(db_session, 999999) == []


def test_get_team_submission_history_empty(db_session: Session, team: Team):
    delete_submissions_for_teams(db_session, [team.id])
    db_session.commit()
    assert get_team_submission_history(db_session, team.id) == []


# ---------------------------------------------------------------------------
# GET /user/get-team-submissions
# ---------------------------------------------------------------------------


def test_get_team_submissions_success(
    client, db_session: Session, team_token: str, team: Team
):
    delete_submissions_for_teams(db_session, [team.id])
    db_session.commit()

    base = utc_now()
    add_submission(db_session, code="v1", timestamp=base, team_id=team.id, duration_ms=10.0)
    add_submission(
        db_session,
        code="v2",
        timestamp=base + timedelta(minutes=1),
        team_id=team.id,
        duration_ms=20.0,
    )
    db_session.commit()

    response = client.get(
        "/user/get-team-submissions",
        headers={"Authorization": f"Bearer {team_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    submissions = data["data"]["submissions"]
    assert len(submissions) == 2
    # Newest first
    assert submissions[0]["code"] == "v2"
    assert submissions[1]["code"] == "v1"
    assert submissions[0]["duration_ms"] == 20.0
    # Timestamps are ISO-formatted strings
    assert isinstance(submissions[0]["timestamp"], str)


def test_get_team_submissions_empty_for_team_with_no_submissions(
    client, db_session: Session, team_token: str, team: Team
):
    delete_submissions_for_teams(db_session, [team.id])
    db_session.commit()

    response = client.get(
        "/user/get-team-submissions",
        headers={"Authorization": f"Bearer {team_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["submissions"] == []


def test_get_team_submissions_unknown_team_returns_empty(client):
    token = create_access_token(
        data={"sub": "ghost_team_2", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.get(
        "/user/get-team-submissions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"


def test_get_team_submissions_unauthorized(client):
    response = client.get("/user/get-team-submissions")
    assert response.status_code == 401


def test_get_team_submissions_invalid_token(client):
    response = client.get(
        "/user/get-team-submissions",
        headers={"Authorization": "Bearer not.a.real.jwt"},
    )
    assert response.status_code == 401
