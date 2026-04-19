"""Tests for POST /institution/league-create with school_league flag."""

from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, League
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def institution_token(db_session: Session) -> str:
    institution = Institution(
        name="school_league_test_institution",
        contact_person="Test Person",
        contact_email="test@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="test_hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    return create_access_token(
        data={
            "sub": institution.name,
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(minutes=30),
    )


@pytest.fixture
def institution_headers(institution_token: str) -> dict:
    return {"Authorization": f"Bearer {institution_token}"}


def test_school_league_create_success(client, institution_headers, db_session):
    resp = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={
            "name": "school_league_happy",
            "game": "greedy_pig",
            "school_league": True,
            "schools": ["Willetton SHS", "Perth Modern"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success", data
    assert data["data"]["school_league"] is True

    league = db_session.exec(
        select(League).where(League.name == "school_league_happy")
    ).first()
    assert league is not None
    assert league.school_league is True
    assert league.schools_config == {
        "source": "static",
        "schools": ["Willetton SHS", "Perth Modern"],
    }


def test_school_league_requires_schools(client, institution_headers):
    resp = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={
            "name": "school_league_empty",
            "game": "greedy_pig",
            "school_league": True,
            "schools": [],
        },
    )
    assert resp.status_code == 422
    assert "at least one school" in str(resp.json()).lower()


def test_non_school_league_ignores_schools(client, institution_headers, db_session):
    resp = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={
            "name": "non_school_with_schools_arg",
            "game": "greedy_pig",
            "school_league": False,
            "schools": ["Should be ignored"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    league = db_session.exec(
        select(League).where(League.name == "non_school_with_schools_arg")
    ).first()
    assert league is not None
    assert league.school_league is False
    assert league.schools_config is None


def test_school_list_dedup_and_strip(client, institution_headers, db_session):
    resp = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={
            "name": "school_league_dedup",
            "game": "greedy_pig",
            "school_league": True,
            "schools": ["  Willetton  ", "Willetton", "", "Perth Modern", "Willetton"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    league = db_session.exec(
        select(League).where(League.name == "school_league_dedup")
    ).first()
    assert league.schools_config["schools"] == ["Willetton", "Perth Modern"]


def test_school_list_rejects_punctuation_only(client, institution_headers):
    resp = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={
            "name": "school_league_punct",
            "game": "greedy_pig",
            "school_league": True,
            "schools": ["!!!"],
        },
    )
    assert resp.status_code == 422
    assert "alphanumeric" in str(resp.json()).lower()


def test_default_school_league_false(client, institution_headers, db_session):
    """Leagues created without the flag default to school_league=False."""
    resp = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={"name": "classic_league", "game": "greedy_pig"},
    )
    assert resp.status_code == 200
    league = db_session.exec(
        select(League).where(League.name == "classic_league")
    ).first()
    assert league.school_league is False
    assert league.schools_config is None
