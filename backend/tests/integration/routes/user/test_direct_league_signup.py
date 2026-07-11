"""Tests for POST /user/direct-league-signup — token-based team creation and auto-login."""

import secrets
from datetime import timedelta

import pytest
from jose import jwt
from sqlmodel import Session, select

from backend.tests.conftest import build_institution
from backend.database.db_models import Institution, League, LeagueType, Team
from backend.routes.auth.auth_config import SECRET_KEY, ALGORITHM
from backend.time_utils import utc_now



@pytest.fixture
def signup_league(db_session: Session) -> dict:
    """Create an institution with a league that has a valid signup token."""
    now = utc_now()

    institution = build_institution(
        name="Signup Test School",
        contact_person="Teacher",
        contact_email="teacher@signup.com",
        created_date=now,
        subscription_active=True,
        subscription_expiry=now + timedelta(days=30),
        password_hash="hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    token = secrets.token_urlsafe(16)
    league = League(
        name="signup_test_league",
        created_date=now,
        expiry_date=now + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
        league_type=LeagueType.INSTITUTION,
        signup_link=token,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    return {"institution": institution, "league": league, "signup_token": token}


@pytest.fixture
def expired_league(db_session: Session) -> dict:
    """Create a league with an expired date and signup token."""
    now = utc_now()

    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()

    token = secrets.token_urlsafe(16)
    league = League(
        name="expired_signup_league",
        created_date=now - timedelta(days=14),
        expiry_date=now - timedelta(days=1),
        game="greedy_pig",
        institution_id=institution.id,
        league_type=LeagueType.INSTITUTION,
        signup_link=token,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    return {"league": league, "signup_token": token}


def test_direct_signup_success(client, signup_league, db_session):
    """Successful signup creates team, assigns to league, and returns a valid token."""
    resp = client.post(
        "/user/direct-league-signup",
        json={
            "team_name": "signup_team_1",
            "password": "securepass123",
            "signup_token": signup_league["signup_token"],
            "school_name": "Test High School",
        },
    )
    assert resp.status_code == 200
    result = resp.json()
    assert "created and assigned" in result["message"]
    assert result["team_name"] == "signup_team_1"
    assert result["league_name"] == "signup_test_league"
    assert result["league_id"] == signup_league["league"].id
    assert "access_token" in result

    # Token is valid and decodable
    decoded = jwt.decode(result["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == "signup_team_1"
    assert decoded["role"] == "student"

    # Team exists in DB linked to correct league and institution
    team = db_session.exec(select(Team).where(Team.name == "signup_team_1")).first()
    assert team is not None
    assert team.league_id == signup_league["league"].id
    assert team.institution_id == signup_league["institution"].id
    assert team.school_name == "Test High School"


def test_direct_signup_token_usable(client, signup_league):
    """The returned token can be used to access authenticated endpoints."""
    resp = client.post(
        "/user/direct-league-signup",
        json={
            "team_name": "signup_token_test",
            "password": "pass123",
            "signup_token": signup_league["signup_token"],
            "school_name": "",
        },
    )
    token = resp.json()["access_token"]

    # Use token to access an authenticated endpoint
    resp = client.get(
        "/user/get-all-leagues",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "leagues" in resp.json()


def test_direct_signup_failures(client, signup_league, expired_league, db_session):
    """Error cases for direct league signup."""
    # Invalid signup token
    resp = client.post(
        "/user/direct-league-signup",
        json={
            "team_name": "fail_team",
            "password": "pass123",
            "signup_token": "nonexistent_token",
            "school_name": "",
        },
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

    # Expired league
    resp = client.post(
        "/user/direct-league-signup",
        json={
            "team_name": "expired_team",
            "password": "pass123",
            "signup_token": expired_league["signup_token"],
            "school_name": "",
        },
    )
    assert resp.status_code == 410
    assert "expired" in resp.json()["detail"].lower()

    # Duplicate team name — first create one successfully
    client.post(
        "/user/direct-league-signup",
        json={
            "team_name": "dup_team",
            "password": "pass123",
            "signup_token": signup_league["signup_token"],
            "school_name": "",
        },
    )
    # Try again with same name
    resp = client.post(
        "/user/direct-league-signup",
        json={
            "team_name": "dup_team",
            "password": "pass456",
            "signup_token": signup_league["signup_token"],
            "school_name": "",
        },
    )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()

    # Empty team name
    resp = client.post(
        "/user/direct-league-signup",
        json={
            "team_name": "",
            "password": "pass123",
            "signup_token": signup_league["signup_token"],
            "school_name": "",
        },
    )
    assert resp.status_code == 422

    # Empty password
    resp = client.post(
        "/user/direct-league-signup",
        json={
            "team_name": "empty_pass_team",
            "password": "",
            "signup_token": signup_league["signup_token"],
            "school_name": "",
        },
    )
    assert resp.status_code == 422
