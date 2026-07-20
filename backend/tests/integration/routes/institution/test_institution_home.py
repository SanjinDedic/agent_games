from datetime import timedelta

import pytest
from sqlmodel import Session

from backend.database.db_models import (League, LeagueTutorial, Team,
                                        Tutorial)
from backend.routes.auth.auth_core import create_access_token
from backend.tests.conftest import build_institution
from backend.time_utils import utc_now


@pytest.fixture
def home_setup(db_session: Session) -> tuple:
    """Institution with an active league (teams + tutorials), an expired
    league, and the 'unassigned' holding league."""
    institution = build_institution(
        name="home_test_institution",
        password_hash="test_hash",
        created_date=utc_now(),
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    active_league = League(
        name="year9_code_club",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
        signup_link="active-signup-token",
        institution_id=institution.id,
    )
    expired_league = League(
        name="last_term",
        created_date=utc_now() - timedelta(days=120),
        expiry_date=utc_now() - timedelta(days=30),
        game="prisoners_dilemma",
        institution_id=institution.id,
    )
    unassigned = League(
        name="unassigned",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=365),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add_all([active_league, expired_league, unassigned])
    db_session.commit()

    for i in range(3):
        db_session.add(
            Team(
                name=f"home_team_{i}",
                school_name="Test School",
                password_hash="test_hash",
                league_id=active_league.id,
                institution_id=institution.id,
            )
        )
    db_session.add(
        Team(
            name="parked_team",
            school_name="Test School",
            password_hash="test_hash",
            league_id=unassigned.id,
            institution_id=institution.id,
        )
    )

    tut_a = Tutorial(title="Home Test Printing")
    tut_b = Tutorial(title="Home Test Variables")
    db_session.add_all([tut_a, tut_b])
    db_session.commit()
    db_session.add_all(
        [
            LeagueTutorial(league_id=active_league.id, tutorial_id=tut_a.id),
            LeagueTutorial(league_id=active_league.id, tutorial_id=tut_b.id),
        ]
    )
    db_session.commit()

    token = create_access_token(
        data={
            "sub": institution.name,
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(minutes=30),
    )
    return institution, {"Authorization": f"Bearer {token}"}


def test_home_success(client, home_setup):
    institution, headers = home_setup

    response = client.get("/institution/home", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Subscription summary matches the /subscription payload shape
    assert data["institution_name"] == institution.name
    assert data["subscription"]["subscription_active"] is True
    assert "tier" in data["subscription"]

    # The 'unassigned' holding league is excluded
    classrooms = {c["name"]: c for c in data["classrooms"]}
    assert set(classrooms) == {"year9_code_club", "last_term"}

    active = classrooms["year9_code_club"]
    assert active["game"] == "greedy_pig"
    assert active["team_count"] == 3
    assert [t["title"] for t in active["tutorials"]] == [
        "Home Test Printing",
        "Home Test Variables",
    ]
    assert all(isinstance(t["id"], int) for t in active["tutorials"])
    assert active["signup_link"] == "active-signup-token"
    assert active["is_active"] is True

    expired = classrooms["last_term"]
    assert expired["team_count"] == 0
    assert expired["tutorials"] == []
    assert expired["signup_link"] is None
    assert expired["is_active"] is False


def test_home_failures(client, home_setup):
    institution, _ = home_setup

    # No token
    response = client.get("/institution/home")
    assert response.status_code == 401

    # Wrong role
    student_token = create_access_token(
        data={"sub": "some_team", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.get(
        "/institution/home",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403

    # Institution token missing its institution_id
    incomplete_token = create_access_token(
        data={"sub": institution.name, "role": "institution"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.get(
        "/institution/home",
        headers={"Authorization": f"Bearer {incomplete_token}"},
    )
    assert response.status_code == 400
