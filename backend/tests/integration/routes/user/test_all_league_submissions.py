"""Tests for GET /user/get-all-league-submissions/{league_id}."""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.tests.conftest import add_submission
from backend.database.db_models import (
    League,
    Team,
    TeamType,
)
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


@pytest.fixture
def league_with_submissions(db_session: Session) -> dict:
    """Create a league with 2 teams and multiple submissions each."""

    league = League(
        name="submissions_test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    teams = []
    for i in range(2):
        team = Team(
            name=f"sub_test_team_{i}",
            school_name=f"Sub School {i}",
            password_hash="hash",
            league_id=league.id,
            team_type=TeamType.STUDENT,
        )
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)
        teams.append(team)

        # Add 3 submissions per team with ascending timestamps
        base_time = utc_now() - timedelta(hours=3)
        for j in range(3):
            add_submission(
                db_session,
                code=f"# submission {j} for team {i}",
                timestamp=base_time + timedelta(hours=j),
                team_id=team.id,
            )
    db_session.commit()

    # Empty league (no teams)
    empty_league = League(
        name="empty_submissions_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(empty_league)
    db_session.commit()
    db_session.refresh(empty_league)

    token = create_access_token(
        data={"sub": "test_owner", "role": "owner"},
        expires_delta=timedelta(minutes=30),
    )

    return {
        "league": league,
        "empty_league": empty_league,
        "teams": teams,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def test_get_all_submissions_success(client, league_with_submissions):
    """Returns all submissions for all teams with correct structure."""
    data = league_with_submissions
    resp = client.get(
        f"/user/get-all-league-submissions/{data['league'].id}",
        headers=data["headers"],
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["league_name"] == "submissions_test_league"

    teams = payload["teams"]
    assert "sub_test_team_0" in teams
    assert "sub_test_team_1" in teams

    # Each team has 3 submissions
    for team_name in ["sub_test_team_0", "sub_test_team_1"]:
        subs = teams[team_name]
        assert len(subs) == 3

        # Each submission has the required fields
        for sub in subs:
            assert "code" in sub
            assert "timestamp" in sub
            assert "id" in sub

        # Submissions are ordered ascending by timestamp
        timestamps = [s["timestamp"] for s in subs]
        assert timestamps == sorted(timestamps)


def test_get_all_submissions_empty_league(client, league_with_submissions):
    """League with no teams returns empty teams dict."""
    data = league_with_submissions
    resp = client.get(
        f"/user/get-all-league-submissions/{data['empty_league'].id}",
        headers=data["headers"],
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["teams"] == {}
    assert result["league_name"] == "empty_submissions_league"


def test_get_all_submissions_no_auth(client, league_with_submissions):
    """No auth token returns 401."""
    resp = client.get(
        f"/user/get-all-league-submissions/{league_with_submissions['league'].id}"
    )
    assert resp.status_code == 401


def test_get_all_submissions_invalid_league(client, league_with_submissions):
    """Non-existent league_id returns an error."""
    resp = client.get(
        "/user/get-all-league-submissions/99999",
        headers=league_with_submissions["headers"],
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_get_all_submissions_student_forbidden(client, league_with_submissions):
    """Student role is rejected by require_owner."""
    data = league_with_submissions
    student_token = create_access_token(
        data={"sub": "some_student", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    resp = client.get(
        f"/user/get-all-league-submissions/{data['league'].id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403


def test_get_all_submissions_owner_sees_league(client, db_session):
    """The owner can see submissions in any league."""
    db_session.commit()

    league = League(
        name="owned_league",
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
    resp = client.get(
        f"/user/get-all-league-submissions/{league.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["league_name"] == "owned_league"

