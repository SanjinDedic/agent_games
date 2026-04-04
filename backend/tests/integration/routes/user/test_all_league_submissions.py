"""Tests for GET /user/get-all-league-submissions/{league_id}."""

from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    Institution,
    League,
    Submission,
    Team,
    TeamType,
)
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def league_with_submissions(db_session: Session) -> dict:
    """Create a league with 2 teams and multiple submissions each."""
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()

    league = League(
        name="submissions_test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
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
            institution_id=institution.id,
            team_type=TeamType.STUDENT,
        )
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)
        teams.append(team)

        # Add 3 submissions per team with ascending timestamps
        base_time = datetime.now() - timedelta(hours=3)
        for j in range(3):
            db_session.add(Submission(
                code=f"# submission {j} for team {i}",
                timestamp=base_time + timedelta(hours=j),
                team_id=team.id,
            ))
    db_session.commit()

    # Empty league (no teams)
    empty_league = League(
        name="empty_submissions_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(empty_league)
    db_session.commit()
    db_session.refresh(empty_league)

    token = create_access_token(
        data={"sub": "admin", "role": "admin"},
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
    result = resp.json()
    assert result["status"] == "success"

    payload = result["data"]
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
    assert result["status"] == "success"
    assert result["data"]["teams"] == {}
    assert result["data"]["league_name"] == "empty_submissions_league"


def test_get_all_submissions_no_auth(client, league_with_submissions):
    """No auth token returns 401."""
    resp = client.get(
        f"/user/get-all-league-submissions/{league_with_submissions['league'].id}"
    )
    assert resp.status_code == 401


def test_get_all_submissions_invalid_league(client, league_with_submissions):
    """Non-existent league_id returns success with null league_name."""
    resp = client.get(
        "/user/get-all-league-submissions/99999",
        headers=league_with_submissions["headers"],
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["status"] == "success"
    assert result["data"]["league_name"] is None
    assert result["data"]["teams"] == {}
