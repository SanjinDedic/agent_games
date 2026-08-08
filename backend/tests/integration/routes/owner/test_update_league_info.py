from datetime import timedelta

import pytest
from sqlmodel import Session


from backend.database.db_models import League
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def info_setup(db_session: Session) -> tuple:
    db_session.commit()

    league = League(
        name="info_test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    token = create_access_token(
        data={
            "sub": "test_owner",
            "role": "owner",
        },
        expires_delta=timedelta(minutes=30),
    )
    headers = {"Authorization": f"Bearer {token}"}
    return league, headers


def test_update_league_info_success(client, info_setup, db_session):
    league, headers = info_setup

    markdown = "# Schedule\n\nSimulations run every Friday 5pm."
    response = client.post(
        "/owner/update-league-info",
        headers=headers,
        json={"league_id": league.id, "info_markdown": markdown},
    )
    assert response.status_code == 200

    db_session.refresh(league)
    assert league.info_markdown == markdown

    # Empty string clears the field
    response = client.post(
        "/owner/update-league-info",
        headers=headers,
        json={"league_id": league.id, "info_markdown": ""},
    )
    assert response.status_code == 200
    db_session.refresh(league)
    assert league.info_markdown == ""


def test_update_league_info_unknown_league_404(client, info_setup):
    _, headers = info_setup

    response = client.post(
        "/owner/update-league-info",
        headers=headers,
        json={"league_id": 999999, "info_markdown": "should fail"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_update_league_info_unauthenticated(client, info_setup):
    league, _ = info_setup
    response = client.post(
        "/owner/update-league-info",
        json={"league_id": league.id, "info_markdown": "x"},
    )
    assert response.status_code == 401


def test_update_league_info_wrong_role(client, info_setup):
    league, _ = info_setup
    student = create_access_token(
        data={"sub": "s", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/owner/update-league-info",
        headers={"Authorization": f"Bearer {student}"},
        json={"league_id": league.id, "info_markdown": "x"},
    )
    assert response.status_code == 403


def test_update_league_info_not_found(client, info_setup):
    _, headers = info_setup
    response = client.post(
        "/owner/update-league-info",
        headers=headers,
        json={"league_id": 999999, "info_markdown": "x"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
