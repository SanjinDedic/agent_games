"""Tests for POST /institution/league-create with school_league flag."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

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


def test_school_league_requires_a_source(client, institution_headers):
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
    assert "exactly one source" in str(resp.json()).lower()


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


def _mock_csv_response(csv_text: str) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.text = csv_text
    resp.raise_for_status = MagicMock(return_value=None)
    return resp


def test_school_league_create_with_sheet_url(client, institution_headers, db_session):
    csv_text = "School\nWilletton SHS\nPerth Modern\n"
    with patch(
        "backend.schools.providers.httpx.get",
        return_value=_mock_csv_response(csv_text),
    ):
        resp = client.post(
            "/institution/league-create",
            headers=institution_headers,
            json={
                "name": "sheet_backed_league",
                "game": "greedy_pig",
                "school_league": True,
                "sheet_url": "https://docs.google.com/spreadsheets/d/abc123/edit#gid=0",
            },
        )
    assert resp.status_code == 200, resp.json()
    assert resp.json()["status"] == "success"
    league = db_session.exec(
        select(League).where(League.name == "sheet_backed_league")
    ).first()
    assert league.school_league is True
    assert league.schools_config == {
        "source": "google_sheets",
        "sheet_url": "https://docs.google.com/spreadsheets/d/abc123/edit#gid=0",
    }


def test_school_league_rejects_both_sheet_and_static(client, institution_headers):
    resp = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={
            "name": "both_sources",
            "game": "greedy_pig",
            "school_league": True,
            "schools": ["Willetton"],
            "sheet_url": "https://docs.google.com/spreadsheets/d/abc/edit",
        },
    )
    assert resp.status_code == 422
    assert "exactly one source" in str(resp.json()).lower()


def test_school_league_rejects_neither_source(client, institution_headers):
    resp = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={
            "name": "no_source",
            "game": "greedy_pig",
            "school_league": True,
        },
    )
    assert resp.status_code == 422
    assert "exactly one source" in str(resp.json()).lower()


def test_school_league_rejects_empty_sheet(client, institution_headers):
    csv_text = "School\n"  # header only, no data rows
    with patch(
        "backend.schools.providers.httpx.get",
        return_value=_mock_csv_response(csv_text),
    ):
        resp = client.post(
            "/institution/league-create",
            headers=institution_headers,
            json={
                "name": "empty_sheet_league",
                "game": "greedy_pig",
                "school_league": True,
                "sheet_url": "https://docs.google.com/spreadsheets/d/empty/edit",
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "empty list" in body["message"].lower()


def test_school_league_rejects_unreachable_sheet(client, institution_headers):
    with patch(
        "backend.schools.providers.httpx.get",
        side_effect=RuntimeError("boom"),
    ):
        resp = client.post(
            "/institution/league-create",
            headers=institution_headers,
            json={
                "name": "unreachable_sheet_league",
                "game": "greedy_pig",
                "school_league": True,
                "sheet_url": "https://docs.google.com/spreadsheets/d/unreachable/edit",
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "could not read the google sheet" in body["message"].lower()


def test_school_league_rejects_non_sheets_url(client, institution_headers):
    resp = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={
            "name": "bad_url_league",
            "game": "greedy_pig",
            "school_league": True,
            "sheet_url": "https://example.com/some-random-page",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "google sheets url" in body["message"].lower()
