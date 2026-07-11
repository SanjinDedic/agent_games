from datetime import timedelta

import pytest
from sqlmodel import Session

from backend.tests.conftest import build_institution
from backend.database.db_models import Institution, League
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now



@pytest.fixture
def info_setup(db_session: Session) -> tuple:
    institution = build_institution(
        name="info_test_institution",
        contact_person="Test Person",
        contact_email="test@example.com",
        created_date=utc_now(),
        subscription_active=True,
        subscription_expiry=utc_now() + timedelta(days=30),
        password_hash="test_hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    league = League(
        name="info_test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    token = create_access_token(
        data={
            "sub": institution.name,
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(minutes=30),
    )
    headers = {"Authorization": f"Bearer {token}"}
    return institution, league, headers


def test_update_league_info_success(client, info_setup, db_session):
    institution, league, headers = info_setup

    markdown = "# Schedule\n\nSimulations run every Friday 5pm."
    response = client.post(
        "/institution/update-league-info",
        headers=headers,
        json={"league_id": league.id, "info_markdown": markdown},
    )
    assert response.status_code == 200

    db_session.refresh(league)
    assert league.info_markdown == markdown

    # Empty string clears the field
    response = client.post(
        "/institution/update-league-info",
        headers=headers,
        json={"league_id": league.id, "info_markdown": ""},
    )
    assert response.status_code == 200
    db_session.refresh(league)
    assert league.info_markdown == ""


def test_update_league_info_cross_institution_rejected(client, info_setup, db_session):
    institution, league, headers = info_setup

    other = build_institution(
        name="other_info_institution",
        contact_person="Other",
        contact_email="other@example.com",
        created_date=utc_now(),
        subscription_active=True,
        subscription_expiry=utc_now() + timedelta(days=30),
        password_hash="test_hash",
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    other_league = League(
        name="other_info_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=other.id,
    )
    db_session.add(other_league)
    db_session.commit()
    db_session.refresh(other_league)

    # institution from info_setup tries to edit other's league
    response = client.post(
        "/institution/update-league-info",
        headers=headers,
        json={"league_id": other_league.id, "info_markdown": "should fail"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    db_session.refresh(other_league)
    assert other_league.info_markdown == ""


def test_update_league_info_unauthenticated(client, info_setup):
    _, league, _ = info_setup
    response = client.post(
        "/institution/update-league-info",
        json={"league_id": league.id, "info_markdown": "x"},
    )
    assert response.status_code == 401


def test_update_league_info_wrong_role(client, info_setup):
    _, league, _ = info_setup
    student = create_access_token(
        data={"sub": "s", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/institution/update-league-info",
        headers={"Authorization": f"Bearer {student}"},
        json={"league_id": league.id, "info_markdown": "x"},
    )
    assert response.status_code == 403


def test_update_league_info_not_found(client, info_setup):
    _, _, headers = info_setup
    response = client.post(
        "/institution/update-league-info",
        headers=headers,
        json={"league_id": 999999, "info_markdown": "x"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
