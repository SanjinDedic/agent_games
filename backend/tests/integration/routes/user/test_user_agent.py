from datetime import timedelta

import pytest
from sqlmodel import Session, delete, select

import backend.routes.user.user_router as user_router_module
from backend.database.db_models import League, Submission, SubmissionMetadata, Team
from backend.database.submission_helpers import delete_submissions_for_teams
from backend.routes.ai.ai_models import Hint
from backend.routes.ai.hint_service import (
    HINT_COOLDOWN,
    SUBMISSIONS_BETWEEN_HINTS,
    hint_available,
)
from backend.routes.auth.auth_core import create_access_token
from backend.routes.user.user_db import get_team_by_id
from backend.tests.conftest import (
    add_failed_submission,
    add_submission,
    make_student_token,
)
from backend.time_utils import utc_now


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
            created_date=utc_now(),
            expiry_date=utc_now() + timedelta(days=7),
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
    return make_student_token(setup_test_team)


def test_submit_agent_success(
    client, db_session: Session, student_token: str, setup_test_team: Team
):
    """Test successful agent submission scenarios"""

    # Verify team is properly set up
    team = get_team_by_id(db_session, setup_test_team.id)
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
    assert data["submission_id"] is not None
    assert "results" in data
    assert "feedback" in data

    # Verify submission was saved
    latest_submission = db_session.exec(
        select(Submission)
        .join(SubmissionMetadata, Submission.metadata_id == SubmissionMetadata.id)
        .where(SubmissionMetadata.team_id == team.id)
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
    assert response.json()["submission_id"] is not None


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
    assert response.status_code == 400
    assert "Agent code is not safe" in response.json()["detail"]

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
    assert response.status_code == 400
    assert "syntax error" in response.json()["detail"].lower()

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
    auth_headers,
    setup_test_league: League,
    setup_test_team: Team,
):
    """Test successful retrieval of league submissions"""

    # Add some test submissions
    add_submission(
        db_session, code="test code 1", timestamp=utc_now(), team_id=setup_test_team.id
    )
    add_submission(
        db_session,
        code="test code 2",
        timestamp=utc_now() + timedelta(minutes=1),
        team_id=setup_test_team.id,
    )
    db_session.commit()

    # Verify submissions were added
    submissions = db_session.exec(
        select(Submission)
        .join(SubmissionMetadata, Submission.metadata_id == SubmissionMetadata.id)
        .where(SubmissionMetadata.team_id == setup_test_team.id)
    ).all()
    assert len(submissions) == 2

    # Get league submissions (admin bypasses ownership)
    response = client.get(
        f"/user/get-league-submissions/{setup_test_league.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert setup_test_team.name in data
    assert (
        data[setup_test_team.name] == "test code 2"
    )  # Should get latest submission


def test_get_league_submissions_exceptions(client, student_token: str, auth_headers):
    """Test error cases for getting league submissions"""

    # Test case 1: Admin gets empty dict for non-existent league
    response = client.get(
        "/user/get-league-submissions/99999",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == {}

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

    # Test case 4: Student role is no longer allowed
    response = client.get(
        "/user/get-league-submissions/1",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403


def test_get_team_submission_success(
    client, db_session: Session, student_token: str, setup_test_team: Team
):
    """Test successful retrieval of team submission"""

    # First verify team exists
    team = db_session.exec(select(Team).where(Team.id == setup_test_team.id)).first()
    assert team is not None

    # Add test submissions
    add_submission(
        db_session,
        code="old code",
        timestamp=utc_now(),
        team_id=team.id,
        league_id=team.league_id,
    )
    db_session.commit()

    add_submission(
        db_session,
        code="latest code",
        timestamp=utc_now() + timedelta(minutes=1),
        team_id=team.id,
        league_id=team.league_id,
    )
    db_session.commit()

    # Verify submissions were added
    submissions = db_session.exec(
        select(Submission)
        .join(SubmissionMetadata, Submission.metadata_id == SubmissionMetadata.id)
        .where(SubmissionMetadata.team_id == team.id)
    ).all()
    assert len(submissions) == 2

    # Get team submission
    response = client.get(
        "/user/get-team-submission",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    assert response.json()["code"] == "latest code"


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

    # Test case 3: Token without team_id surfaces the route's guard
    non_existent_token = create_access_token(
        data={"sub": "non_existent_team", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.get(
        "/user/get-team-submission",
        headers={"Authorization": f"Bearer {non_existent_token}"},
    )
    assert response.status_code == 400
    assert "team token" in response.json()["detail"]


def _make_hints_available(db_session: Session, team_id: int) -> None:
    """Seed old failed attempts: enough to pass the submissions-between-hints
    gap and old enough to pass the cooldown, so hint rationing allows a hint."""
    base = utc_now() - timedelta(seconds=HINT_COOLDOWN + 60)
    for i in range(SUBMISSIONS_BETWEEN_HINTS):
        add_failed_submission(
            db_session, timestamp=base + timedelta(seconds=i), team_id=team_id
        )
    db_session.commit()


def test_submit_agent_hint_cancelled_on_valid_code(
    client,
    db_session: Session,
    student_token: str,
    setup_test_team: Team,
    monkeypatch,
):
    """A hint requested alongside code that passes validation is cancelled:
    no LLM call, the attempt isn't consumed, and the response says so."""
    _make_hints_available(db_session, setup_test_team.id)

    async def fail_provide_hints(*args, **kwargs):
        raise AssertionError("provide_hints must not be called for valid code")

    monkeypatch.setattr(user_router_module, "provide_hints", fail_provide_hints)

    valid_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
"""
    response = client.post(
        "/user/submit-agent?generate_hint=true",
        json={"code": valid_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["hint"] is None
    assert data["hint_available"] is False
    assert data["hint_cancelled"] is True

    latest_meta = db_session.exec(
        select(SubmissionMetadata)
        .where(SubmissionMetadata.team_id == setup_test_team.id)
        .order_by(SubmissionMetadata.id.desc())
    ).first()
    assert latest_meta.hint_included is False

    # The ration wasn't spent, so a hint is still available for a future
    # failed attempt.
    assert hint_available(db_session, setup_test_team) is True


def test_submit_agent_hint_returned_when_validation_fails(
    client,
    db_session: Session,
    student_token: str,
    setup_test_team: Team,
    monkeypatch,
):
    """A hint requested alongside failing code is generated, returned in the
    400 body, and consumes the hint attempt."""
    _make_hints_available(db_session, setup_test_team.id)

    fake_hint = Hint(
        line_number=1,
        quoted_line="import os",
        assumptions=["the sandbox allows importing os"],
        small_hint="Is the os module available to agent code?",
        big_hint="Agent code cannot import os; remove the import.",
        priority=1,
        bug=True,
    )

    async def fake_provide_hints(*args, **kwargs):
        return [fake_hint]

    monkeypatch.setattr(user_router_module, "provide_hints", fake_provide_hints)

    unsafe_code = """
import os
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
"""
    response = client.post(
        "/user/submit-agent?generate_hint=true",
        json={"code": unsafe_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["hint"]["small_hint"] == fake_hint.small_hint
    assert data["hint_available"] is False

    latest_meta = db_session.exec(
        select(SubmissionMetadata)
        .where(SubmissionMetadata.team_id == setup_test_team.id)
        .order_by(SubmissionMetadata.id.desc())
    ).first()
    assert latest_meta.hint_included is True


def test_submit_agent_hint_request_rejected_when_unavailable(
    client, student_token: str, setup_test_team: Team
):
    """With no prior attempts, hint rationing denies the request with a 429
    before any validation runs."""
    response = client.post(
        "/user/submit-agent?generate_hint=true",
        json={"code": "irrelevant"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 429
    assert "not allowed to request a hint" in response.json()["detail"]


def test_submit_agent_hint_request_bypasses_rate_limit(
    client,
    db_session: Session,
    student_token: str,
    setup_test_team: Team,
    monkeypatch,
):
    """Hint requests answer to hint rationing only: with the per-minute
    submission limit saturated, a plain submission 429s but a hint request
    still goes through."""
    _make_hints_available(db_session, setup_test_team.id)
    now = utc_now()
    for _ in range(5):
        add_failed_submission(db_session, timestamp=now, team_id=setup_test_team.id)
    db_session.commit()

    # Sanity: a plain submission is rate limited right now
    response = client.post(
        "/user/submit-agent",
        json={"code": "irrelevant"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 429
    assert "per minute" in response.json()["detail"]

    fake_hint = Hint(
        line_number=1,
        quoted_line="import os",
        assumptions=["the sandbox allows importing os"],
        small_hint="Is the os module available to agent code?",
        big_hint="Agent code cannot import os; remove the import.",
        priority=1,
        bug=True,
    )

    async def fake_provide_hints(*args, **kwargs):
        return [fake_hint]

    monkeypatch.setattr(user_router_module, "provide_hints", fake_provide_hints)

    unsafe_code = """
import os
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
"""
    response = client.post(
        "/user/submit-agent?generate_hint=true",
        json={"code": unsafe_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 400
    assert response.json()["hint"]["small_hint"] == fake_hint.small_hint


def test_submit_agent_rate_limit(
    client,
    db_session: Session,
    student_token: str,
    setup_test_team: Team,
):
    """Test submission rate limiting using actual endpoint submissions"""
    # First verify team is properly set up
    team = get_team_by_id(db_session, setup_test_team.id)
    assert team is not None
    assert team.league is not None

    # Clear any existing submissions
    delete_submissions_for_teams(db_session, [team.id])
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
        assert response.json()["submission_id"] == i + 1

    # Verify we have exactly 5 submissions
    submissions = db_session.exec(
        select(Submission)
        .join(SubmissionMetadata, Submission.metadata_id == SubmissionMetadata.id)
        .where(SubmissionMetadata.team_id == team.id)
    ).all()
    assert len(submissions) == 5

    # The 6th submission should fail due to rate limit
    response = client.post(
        "/user/submit-agent",
        json={"code": valid_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 429
    assert "5 submissions per minute" in response.json()["detail"]

    # Verify we still have exactly 5 submissions
    submissions = db_session.exec(
        select(Submission)
        .join(SubmissionMetadata, Submission.metadata_id == SubmissionMetadata.id)
        .where(SubmissionMetadata.team_id == team.id)
    ).all()
    assert len(submissions) == 5
