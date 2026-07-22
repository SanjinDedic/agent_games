from datetime import timedelta

import pytest
from sqlmodel import Session

from backend.database.db_models import League, Team
from backend.routes.auth.auth_core import create_access_token
from backend.tests.conftest import build_institution
from backend.time_utils import utc_now


@pytest.fixture
def reset_setup(db_session: Session) -> dict:
    """Two institutions, each with a league and a team, plus auth headers for
    the first institution."""
    institutions = {}
    for key in ("own", "other"):
        institution = build_institution(
            name=f"{key}_reset_institution",
            password_hash="test_hash",
        )
        db_session.add(institution)
        db_session.commit()
        db_session.refresh(institution)

        league = League(
            name=f"{key}_reset_league",
            created_date=utc_now(),
            expiry_date=utc_now() + timedelta(days=7),
            game="greedy_pig",
            institution_id=institution.id,
        )
        db_session.add(league)
        db_session.commit()
        db_session.refresh(league)

        team = Team(
            name=f"{key}_reset_team",
            school_name="Reset Test School",
            league_id=league.id,
            institution_id=institution.id,
        )
        team.set_password("original_password")
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)

        institutions[key] = {"institution": institution, "team": team}

    own = institutions["own"]["institution"]
    token = create_access_token(
        data={
            "sub": own.name,
            "role": "institution",
            "institution_id": own.id,
        },
        expires_delta=timedelta(minutes=30),
    )

    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "team": institutions["own"]["team"],
        "other_team": institutions["other"]["team"],
    }


def test_generate_reset_link(client, reset_setup, db_session):
    """Generating stores a token on the team; regenerating replaces it."""
    team = reset_setup["team"]

    response = client.post(
        "/institution/team-password-reset",
        headers=reset_setup["headers"],
        json={"team_id": team.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["team_name"] == team.name
    first_token = data["reset_token"]

    db_session.refresh(team)
    assert team.password_reset_token == first_token
    assert team.password_reset_expiry > utc_now()

    response = client.post(
        "/institution/team-password-reset",
        headers=reset_setup["headers"],
        json={"team_id": team.id},
    )
    assert response.status_code == 200
    second_token = response.json()["reset_token"]
    assert second_token != first_token

    db_session.refresh(team)
    assert team.password_reset_token == second_token

    # The replaced token no longer resolves
    assert client.get(f"/user/password-reset-info/{first_token}").status_code == 404


def test_generate_reset_link_failures(client, reset_setup, team_token):
    """Missing team -> 404, foreign team -> 403, student token -> 403."""
    headers = reset_setup["headers"]

    response = client.post(
        "/institution/team-password-reset", headers=headers, json={"team_id": 99999}
    )
    assert response.status_code == 404

    response = client.post(
        "/institution/team-password-reset",
        headers=headers,
        json={"team_id": reset_setup["other_team"].id},
    )
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()

    response = client.post(
        "/institution/team-password-reset",
        headers={"Authorization": f"Bearer {team_token}"},
        json={"team_id": reset_setup["team"].id},
    )
    assert response.status_code == 403


def test_reset_info_public_lookup(client, reset_setup):
    """The public info endpoint names the team; unknown tokens 404."""
    team = reset_setup["team"]
    reset_token = client.post(
        "/institution/team-password-reset",
        headers=reset_setup["headers"],
        json={"team_id": team.id},
    ).json()["reset_token"]

    response = client.get(f"/user/password-reset-info/{reset_token}")
    assert response.status_code == 200
    data = response.json()
    assert data["team_name"] == team.name
    assert data["institution_name"] == "own_reset_institution"
    assert data["is_teacher"] is False

    assert client.get("/user/password-reset-info/not-a-token").status_code == 404


def test_reset_password_full_flow(client, reset_setup, db_session):
    """Consuming the link sets the password, logs the team in, and kills the
    token; the old password stops working."""
    team = reset_setup["team"]
    reset_token = client.post(
        "/institution/team-password-reset",
        headers=reset_setup["headers"],
        json={"team_id": team.id},
    ).json()["reset_token"]

    response = client.post(
        "/user/reset-team-password",
        json={"reset_token": reset_token, "password": "new_password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["team_name"] == team.name
    assert data["team_id"] == team.id

    # The returned token is a working student session
    me = client.get(
        "/user/team-data",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200

    # New password logs in, old one doesn't
    login = client.post(
        "/auth/team-login", json={"name": team.name, "password": "new_password"}
    )
    assert login.status_code == 200
    old_login = client.post(
        "/auth/team-login",
        json={"name": team.name, "password": "original_password"},
    )
    assert old_login.status_code == 401

    # Token is single-use
    db_session.refresh(team)
    assert team.password_reset_token is None
    assert team.password_reset_expiry is None
    response = client.post(
        "/user/reset-team-password",
        json={"reset_token": reset_token, "password": "another_password"},
    )
    assert response.status_code == 404


def test_reset_password_expired_and_invalid(client, reset_setup, db_session):
    """Expired tokens 404; blank passwords 422 without consuming the token."""
    team = reset_setup["team"]
    reset_token = client.post(
        "/institution/team-password-reset",
        headers=reset_setup["headers"],
        json={"team_id": team.id},
    ).json()["reset_token"]

    response = client.post(
        "/user/reset-team-password",
        json={"reset_token": reset_token, "password": "   "},
    )
    assert response.status_code == 422

    team.password_reset_expiry = utc_now() - timedelta(hours=1)
    db_session.add(team)
    db_session.commit()

    assert client.get(f"/user/password-reset-info/{reset_token}").status_code == 404
    response = client.post(
        "/user/reset-team-password",
        json={"reset_token": reset_token, "password": "new_password"},
    )
    assert response.status_code == 404

    # Expiry did not consume the token state, but login is unaffected either way
    login = client.post(
        "/auth/team-login",
        json={"name": team.name, "password": "original_password"},
    )
    assert login.status_code == 200
