"""Tests for school-league flow: GET /user/league-info and POST /user/direct-school-league-signup."""

import secrets
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import pytz
from jose import jwt
from sqlmodel import Session, select

from backend.database.db_models import (
    Institution,
    League,
    LeagueType,
    Team,
    TeamType,
)
from backend.routes.auth.auth_config import ALGORITHM, SECRET_KEY

AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


@pytest.fixture
def school_league_fixture(db_session: Session) -> dict:
    """Create an institution + a school league with a valid signup token."""
    now = datetime.now(AUSTRALIA_SYDNEY_TZ)

    institution = Institution(
        name="School League Test School",
        contact_person="Teacher",
        contact_email="teacher@school.com",
        created_date=now,
        subscription_active=True,
        subscription_expiry=now + timedelta(days=30),
        docker_access=True,
        password_hash="hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    token = secrets.token_urlsafe(16)
    league = League(
        name="school_signup_test_league",
        created_date=now,
        expiry_date=now + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
        league_type=LeagueType.INSTITUTION,
        signup_link=token,
        school_league=True,
        schools_config={
            "source": "static",
            "schools": ["Willetton SHS", "Perth Modern"],
        },
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    return {"institution": institution, "league": league, "signup_token": token}


@pytest.fixture
def non_school_league_fixture(db_session: Session) -> dict:
    now = datetime.now(AUSTRALIA_SYDNEY_TZ)
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()

    token = secrets.token_urlsafe(16)
    league = League(
        name="non_school_league_for_rejection",
        created_date=now,
        expiry_date=now + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
        league_type=LeagueType.INSTITUTION,
        signup_link=token,
        school_league=False,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    return {"league": league, "signup_token": token}


@pytest.fixture
def expired_school_league_fixture(db_session: Session) -> dict:
    now = datetime.now(AUSTRALIA_SYDNEY_TZ)
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()

    token = secrets.token_urlsafe(16)
    league = League(
        name="expired_school_league",
        created_date=now - timedelta(days=14),
        expiry_date=now - timedelta(days=1),
        game="greedy_pig",
        institution_id=institution.id,
        league_type=LeagueType.INSTITUTION,
        signup_link=token,
        school_league=True,
        schools_config={
            "source": "static",
            "schools": ["Willetton SHS"],
        },
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    return {"league": league, "signup_token": token}


def test_league_info_includes_schools(client, school_league_fixture):
    resp = client.get(f"/user/league-info/{school_league_fixture['signup_token']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    payload = data["data"]
    assert payload["school_league"] is True
    assert payload["schools"] == ["Willetton SHS", "Perth Modern"]


def test_league_info_non_school_omits_schools(client, non_school_league_fixture):
    resp = client.get(
        f"/user/league-info/{non_school_league_fixture['signup_token']}"
    )
    assert resp.status_code == 200
    payload = resp.json()["data"]
    assert payload["school_league"] is False
    assert "schools" not in payload


def test_direct_school_signup_happy_path(client, school_league_fixture, db_session):
    resp = client.post(
        "/user/direct-school-league-signup",
        json={
            "signup_token": school_league_fixture["signup_token"],
            "school_name": "Willetton SHS",
            "password": "securepass123",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success", data
    result = data["data"]
    assert result["team_name"] == "WillettonSHS1"
    assert result["league_id"] == school_league_fixture["league"].id

    decoded = jwt.decode(result["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == "WillettonSHS1"
    assert decoded["role"] == "student"

    team = db_session.exec(
        select(Team).where(Team.name == "WillettonSHS1")
    ).first()
    assert team is not None
    assert team.league_id == school_league_fixture["league"].id
    assert team.institution_id == school_league_fixture["institution"].id
    assert team.school_name == "Willetton SHS"


def test_direct_school_signup_counter(client, school_league_fixture):
    token = school_league_fixture["signup_token"]
    r1 = client.post(
        "/user/direct-school-league-signup",
        json={
            "signup_token": token,
            "school_name": "Willetton SHS",
            "password": "pw1",
        },
    )
    r2 = client.post(
        "/user/direct-school-league-signup",
        json={
            "signup_token": token,
            "school_name": "Willetton SHS",
            "password": "pw2",
        },
    )
    assert r1.json()["data"]["team_name"] == "WillettonSHS1"
    assert r2.json()["data"]["team_name"] == "WillettonSHS2"


def test_direct_school_signup_school_not_in_list(client, school_league_fixture):
    resp = client.post(
        "/user/direct-school-league-signup",
        json={
            "signup_token": school_league_fixture["signup_token"],
            "school_name": "Bogus High",
            "password": "pw",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "not in this league" in body["message"].lower()


def test_direct_school_signup_rejects_non_school_league(
    client, non_school_league_fixture
):
    resp = client.post(
        "/user/direct-school-league-signup",
        json={
            "signup_token": non_school_league_fixture["signup_token"],
            "school_name": "Whatever",
            "password": "pw",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "not a school league" in body["message"].lower()


def test_direct_school_signup_expired_league(client, expired_school_league_fixture):
    resp = client.post(
        "/user/direct-school-league-signup",
        json={
            "signup_token": expired_school_league_fixture["signup_token"],
            "school_name": "Willetton SHS",
            "password": "pw",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "expired" in body["message"].lower()


def test_direct_school_signup_invalid_token(client):
    resp = client.post(
        "/user/direct-school-league-signup",
        json={
            "signup_token": "bogus_token_12345",
            "school_name": "Willetton SHS",
            "password": "pw",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"


def test_direct_school_signup_skips_cross_league_collision(
    client, school_league_fixture, db_session
):
    """A WillettonSHS1 in another league forces the counter to skip."""
    other_league = db_session.exec(
        select(League).where(League.name == "unassigned")
    ).first()
    pre_existing = Team(
        name="WillettonSHS1",
        school_name="Willetton SHS",
        password_hash="hash",
        league_id=other_league.id,
        team_type=TeamType.STUDENT,
    )
    db_session.add(pre_existing)
    db_session.commit()

    resp = client.post(
        "/user/direct-school-league-signup",
        json={
            "signup_token": school_league_fixture["signup_token"],
            "school_name": "Willetton SHS",
            "password": "pw",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["team_name"] == "WillettonSHS2"


def test_direct_league_signup_still_works_for_non_school_league(
    client, non_school_league_fixture, db_session
):
    """Regression: the classic team-signup endpoint is unchanged for non-school leagues."""
    resp = client.post(
        "/user/direct-league-signup",
        json={
            "team_name": "classic_regression_team",
            "password": "pw",
            "signup_token": non_school_league_fixture["signup_token"],
            "school_name": "Any School",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    team = db_session.exec(
        select(Team).where(Team.name == "classic_regression_team")
    ).first()
    assert team is not None
    assert team.school_name == "Any School"


@pytest.fixture
def sheet_backed_league_fixture(db_session: Session) -> dict:
    """A school league whose schools_config points at a Google Sheet URL."""
    now = datetime.now(AUSTRALIA_SYDNEY_TZ)
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()

    token = secrets.token_urlsafe(16)
    league = League(
        name="sheet_backed_signup_league",
        created_date=now,
        expiry_date=now + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
        league_type=LeagueType.INSTITUTION,
        signup_link=token,
        school_league=True,
        schools_config={
            "source": "google_sheets",
            "sheet_url": "https://docs.google.com/spreadsheets/d/sheet999/edit#gid=0",
        },
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    return {"league": league, "signup_token": token}


def _mock_csv_response(csv_text: str) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.text = csv_text
    resp.raise_for_status = MagicMock(return_value=None)
    return resp


def test_sheet_backed_league_info_and_signup(
    client, sheet_backed_league_fixture, db_session
):
    csv_text = "School\nWilletton SHS\nPerth Modern\n"
    with patch(
        "backend.schools.providers.httpx.get",
        return_value=_mock_csv_response(csv_text),
    ):
        info = client.get(
            f"/user/league-info/{sheet_backed_league_fixture['signup_token']}"
        )
        assert info.status_code == 200
        payload = info.json()["data"]
        assert payload["school_league"] is True
        assert payload["schools"] == ["Willetton SHS", "Perth Modern"]

        signup = client.post(
            "/user/direct-school-league-signup",
            json={
                "signup_token": sheet_backed_league_fixture["signup_token"],
                "school_name": "Perth Modern",
                "password": "pw",
            },
        )
    assert signup.status_code == 200
    assert signup.json()["status"] == "success"
    assert signup.json()["data"]["team_name"] == "PerthModern1"


def test_sheet_backed_signup_rejects_school_not_in_sheet(
    client, sheet_backed_league_fixture
):
    csv_text = "School\nWilletton SHS\n"
    with patch(
        "backend.schools.providers.httpx.get",
        return_value=_mock_csv_response(csv_text),
    ):
        resp = client.post(
            "/user/direct-school-league-signup",
            json={
                "signup_token": sheet_backed_league_fixture["signup_token"],
                "school_name": "Perth Modern",
                "password": "pw",
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "not in this league" in body["message"].lower()
