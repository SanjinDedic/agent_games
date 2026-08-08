from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import UNASSIGNED_LEAGUE_NAME, League, Team
from backend.routes.auth.auth_core import create_access_token

from backend.time_utils import utc_now


@pytest.fixture
def home_setup(db_session: Session) -> tuple:
    """An active league (with teams), an expired league, and the
    'unassigned' holding league."""
    db_session.commit()

    active_league = League(
        name="year9_code_club",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
        signup_link="active-signup-token",
    )
    expired_league = League(
        name="last_term",
        created_date=utc_now() - timedelta(days=120),
        expiry_date=utc_now() - timedelta(days=30),
        game="prisoners_dilemma",
    )
    db_session.add_all([active_league, expired_league])
    db_session.commit()

    unassigned = db_session.exec(
        select(League).where(League.name == UNASSIGNED_LEAGUE_NAME)
    ).one()
    db_session.commit()

    for i in range(3):
        db_session.add(
            Team(
                name=f"home_team_{i}",
                school_name="Test School",
                password_hash="test_hash",
                league_id=active_league.id,
            )
        )
    db_session.add(
        Team(
            name="parked_team",
            school_name="Test School",
            password_hash="test_hash",
            league_id=unassigned.id,
        )
    )

    db_session.commit()

    token = create_access_token(
        data={
            "sub": "test_owner",
            "role": "owner",
        },
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


def test_home_success(client, home_setup):
    headers = home_setup

    response = client.get("/owner/home", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # The 'unassigned' holding league is excluded
    classrooms = {c["name"]: c for c in data["classrooms"]}
    assert {"year9_code_club", "last_term"} <= set(classrooms)

    active = classrooms["year9_code_club"]
    assert active["game"] == "greedy_pig"
    assert active["team_count"] == 3
    assert active["signup_link"] == "active-signup-token"
    assert active["is_active"] is True

    expired = classrooms["last_term"]
    assert expired["team_count"] == 0
    assert expired["signup_link"] is None
    assert expired["is_active"] is False


def test_home_failures(client, home_setup):
    _ = home_setup

    # No token
    response = client.get("/owner/home")
    assert response.status_code == 401

    # Wrong role
    student_token = create_access_token(
        data={"sub": "some_team", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.get(
        "/owner/home",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403

