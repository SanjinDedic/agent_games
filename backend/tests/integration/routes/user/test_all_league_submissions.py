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
    """Non-existent league_id returns an error (no cross-institution leak)."""
    resp = client.get(
        "/user/get-all-league-submissions/99999",
        headers=league_with_submissions["headers"],
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


def test_get_all_submissions_student_forbidden(client, league_with_submissions):
    """Student role is rejected by verify_admin_or_institution."""
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


def test_get_all_submissions_institution_own_league(client, db_session):
    """An institution can see submissions in a league it owns."""
    institution = Institution(
        name="own_league_inst",
        contact_person="Person",
        contact_email="p@e.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    league = League(
        name="owned_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
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
    resp = client.get(
        f"/user/get-all-league-submissions/{league.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["data"]["league_name"] == "owned_league"


def test_get_all_submissions_institution_cannot_see_other_institution(
    client, db_session
):
    """Institution A cannot read Institution B's league submissions."""
    inst_a = Institution(
        name="inst_a_for_leak_test",
        contact_person="A",
        contact_email="a@e.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="hash",
    )
    inst_b = Institution(
        name="inst_b_for_leak_test",
        contact_person="B",
        contact_email="b@e.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="hash",
    )
    db_session.add(inst_a)
    db_session.add(inst_b)
    db_session.commit()
    db_session.refresh(inst_a)
    db_session.refresh(inst_b)

    # League belongs to inst_b; team + submissions inside it
    b_league = League(
        name="inst_b_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=inst_b.id,
    )
    db_session.add(b_league)
    db_session.commit()
    db_session.refresh(b_league)

    b_team = Team(
        name="secret_team",
        school_name="Secret School",
        password_hash="hash",
        league_id=b_league.id,
        institution_id=inst_b.id,
        team_type=TeamType.STUDENT,
    )
    db_session.add(b_team)
    db_session.commit()
    db_session.refresh(b_team)

    db_session.add(
        Submission(
            code="# secret code",
            timestamp=datetime.now(),
            team_id=b_team.id,
        )
    )
    db_session.commit()

    # Inst A tries to read Inst B's league.
    a_token = create_access_token(
        data={
            "sub": inst_a.name,
            "role": "institution",
            "institution_id": inst_a.id,
        },
        expires_delta=timedelta(minutes=30),
    )
    resp = client.get(
        f"/user/get-all-league-submissions/{b_league.id}",
        headers={"Authorization": f"Bearer {a_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert "permission" in data["message"].lower()
    # Critical: the secret code must NOT leak in the error response.
    assert "secret code" not in resp.text
