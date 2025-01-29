from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, delete, select

from backend.database.db_models import League, Submission, Team
from backend.routes.auth.auth_core import AUSTRALIA_SYDNEY_TZ, create_access_token
from backend.routes.user.user_db import get_team


@pytest.fixture
def setup_test_league(db_session: Session) -> League:
    """Create a test league with correct game type"""
    # First check if league exists
    league = db_session.exec(
        select(League).where(League.name == "test_submit_league")
    ).first()

    if not league:
        league = League(
            name="test_submit_league",
            game="prisoners_dilemma",  # Match the game type with test code
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=7),
        )
        db_session.add(league)
        db_session.commit()
        db_session.refresh(league)

    return league


@pytest.fixture
def setup_test_team(db_session: Session, setup_test_league: League) -> Team:
    """Create a test team properly linked to the test league"""
    # First check if team exists
    team = db_session.exec(select(Team).where(Team.name == "test_submit_team")).first()

    if not team:
        team = Team(
            name="test_submit_team",
            school_name="Test School",
            password_hash="test_hash",  # In real tests this would be properly hashed
            league_id=setup_test_league.id,
        )
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)

    return team


@pytest.fixture
def student_token(setup_test_team: Team) -> str:
    """Create a valid student token for the test team"""
    return create_access_token(
        data={"sub": setup_test_team.name, "role": "student"},
        expires_delta=timedelta(minutes=30),
    )


def test_submit_agent_success(
    client, db_session: Session, student_token: str, setup_test_team: Team
):
    """Test successful agent submission scenarios"""

    # Verify team is properly set up
    team = get_team(db_session, setup_test_team.name)
    assert team is not None
    assert team.league is not None
    assert team.league.game == "prisoners_dilemma"  # Verify game type matches test code

    # Test case 1: Basic valid submission
    valid_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
"""
    response = client.post(
        "/user/submit-agent",
        json={"code": valid_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Submission ID:" in data["message"]
    assert "results" in data["data"]
    assert "feedback" in data["data"]

    # Verify submission was saved
    latest_submission = db_session.exec(
        select(Submission)
        .where(Submission.team_id == team.id)
        .order_by(Submission.timestamp.desc())
    ).first()
    assert latest_submission is not None
    assert latest_submission.code == valid_code

    # Test case 2: Submission with complex strategy
    complex_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if not game_state["opponent_history"]:
            return "collude"
        if "defect" in game_state["opponent_history"]:
            return "defect"
        return "collude"
"""
    response = client.post(
        "/user/submit-agent",
        json={"code": complex_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_submit_agent_exceptions(
    client,
    student_token: str,
):
    """Test error cases for agent submission"""

    # Test case 1: Submit unsafe code
    unsafe_code = """
import os
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        os.system("rm -rf /")  # Unsafe system call
        return "collude"
"""
    response = client.post(
        "/user/submit-agent",
        json={"code": unsafe_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "Agent code is not safe" in data["message"]

    # Test case 2: Submit with syntax error
    invalid_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state)
        return "collude"  # Missing colon
"""
    response = client.post(
        "/user/submit-agent",
        json={"code": invalid_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "syntax error" in data["message"].lower()

    # Test case 3: Submit without authorization
    response = client.post("/user/submit-agent", json={"code": "valid_code"})
    assert response.status_code == 401

    # Test case 4: Submit with wrong token type
    admin_token = create_access_token(
        data={"sub": "admin", "role": "admin"}, expires_delta=timedelta(minutes=30)
    )
    response = client.post(
        "/user/submit-agent",
        json={"code": "valid_code"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403


def test_get_league_submissions_success(
    client,
    db_session: Session,
    student_token: str,
    setup_test_league: League,
    setup_test_team: Team,
):
    """Test successful retrieval of league submissions"""

    # Add some test submissions
    submission1 = Submission(
        code="test code 1", timestamp=datetime.now(), team_id=setup_test_team.id
    )
    submission2 = Submission(
        code="test code 2",
        timestamp=datetime.now() + timedelta(minutes=1),
        team_id=setup_test_team.id,
    )
    db_session.add(submission1)
    db_session.add(submission2)
    db_session.commit()

    # Verify submissions were added
    submissions = db_session.exec(
        select(Submission).where(Submission.team_id == setup_test_team.id)
    ).all()
    assert len(submissions) == 2

    # Get league submissions
    response = client.get(
        f"/user/get-league-submissions/{setup_test_league.id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert setup_test_team.name in data["data"]
    assert (
        data["data"][setup_test_team.name] == "test code 2"
    )  # Should get latest submission


def test_get_league_submissions_exceptions(client, student_token: str):
    """Test error cases for getting league submissions"""

    # Test case 1: Get submissions for non-existent league
    response = client.get(
        "/user/get-league-submissions/99999",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert not data["data"]  # Should be empty dict

    # Test case 2: Unauthorized access (no token)
    response = client.get("/user/get-league-submissions/1")
    assert response.status_code == 401

    # Test case 3: Invalid token
    invalid_token = "invalid.token.here"
    response = client.get(
        "/user/get-league-submissions/1",
        headers={"Authorization": f"Bearer {invalid_token}"},
    )
    assert response.status_code == 401


def test_get_team_submission_success(
    client, db_session: Session, student_token: str, setup_test_team: Team
):
    """Test successful retrieval of team submission"""

    # First verify team exists
    team = db_session.exec(select(Team).where(Team.id == setup_test_team.id)).first()
    assert team is not None

    # Add test submissions
    submission1 = Submission(code="old code", timestamp=datetime.now(), team_id=team.id)
    db_session.add(submission1)
    db_session.commit()

    submission2 = Submission(
        code="latest code",
        timestamp=datetime.now() + timedelta(minutes=1),
        team_id=team.id,
    )
    db_session.add(submission2)
    db_session.commit()

    # Verify submissions were added
    submissions = db_session.exec(
        select(Submission).where(Submission.team_id == team.id)
    ).all()
    assert len(submissions) == 2

    # Get team submission
    response = client.get(
        "/user/get-team-submission",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["code"] == "latest code"


def test_get_team_submission_exceptions(client):
    """Test error cases for getting team submission"""

    # Test case 1: Unauthorized access
    response = client.get("/user/get-team-submission")
    assert response.status_code == 401

    # Test case 2: Invalid token
    invalid_token = "invalid.token.here"
    response = client.get(
        "/user/get-team-submission",
        headers={"Authorization": f"Bearer {invalid_token}"},
    )
    assert response.status_code == 401

    # Test case 3: Non-existent team
    non_existent_token = create_access_token(
        data={"sub": "non_existent_team", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.get(
        "/user/get-team-submission",
        headers={"Authorization": f"Bearer {non_existent_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["code"] is None


def test_submit_agent_rate_limit(
    client,
    db_session: Session,
    student_token: str,
    setup_test_team: Team,
):
    """Test submission rate limiting using actual endpoint submissions"""
    # First verify team is properly set up
    team = get_team(db_session, setup_test_team.name)
    assert team is not None
    assert team.league is not None

    # Clear any existing submissions
    db_session.exec(delete(Submission).where(Submission.team_id == team.id))
    db_session.commit()

    valid_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
"""
    # Make 5 quick submissions through the endpoint
    for i in range(5):
        response = client.post(
            "/user/submit-agent",
            json={"code": valid_code},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert f"Submission ID: {i+1}" in data["message"]

    # Verify we have exactly 5 submissions
    submissions = db_session.exec(
        select(Submission).where(Submission.team_id == team.id)
    ).all()
    assert len(submissions) == 5

    # The 6th submission should fail due to rate limit
    response = client.post(
        "/user/submit-agent",
        json={"code": valid_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "5 submissions per minute" in data["message"]

    # Verify we still have exactly 5 submissions
    submissions = db_session.exec(
        select(Submission).where(Submission.team_id == team.id)
    ).all()
    assert len(submissions) == 5
