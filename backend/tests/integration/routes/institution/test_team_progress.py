"""The /institution/team-progress endpoint: per-team agent submission stats
plus per-tutorial exercise completion counts, scoped to the caller's
institution."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlmodel import Session

from backend.database.db_models import (
    Exercise,
    ExerciseSubmission,
    ExerciseSubmissionMetadata,
    League,
    LeagueTutorial,
    Team,
    Tutorial,
)
from backend.routes.auth.auth_core import create_access_token
from backend.tests.conftest import (
    add_failed_submission,
    add_submission,
    create_test_institution,
)
from backend.time_utils import utc_now


def add_exercise_attempt(
    db_session: Session, team_id: int, exercise_id: int, passed=None
):
    """One attempt: metadata-only when passed is None, otherwise a stored run."""
    now = utc_now()
    meta = ExerciseSubmissionMetadata(
        team_id=team_id, exercise_id=exercise_id, timestamp=now
    )
    db_session.add(meta)
    if passed is not None:
        db_session.flush()
        db_session.add(
            ExerciseSubmission(
                code="def solve(): pass",
                timestamp=now,
                passed=passed,
                test_results=[],
                metadata_id=meta.id,
            )
        )


@pytest.fixture
def progress_setup(db_session: Session) -> SimpleNamespace:
    """An institution with two leagues, a tutorial attached to one of them,
    and three teams with a mix of agent and exercise submissions."""
    institution = create_test_institution(
        db_session, name="progress_institution", password_hash="test_hash"
    )

    league_a = League(
        name="progress_league_a",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    league_b = League(
        name="progress_league_b",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(league_a)
    db_session.add(league_b)
    db_session.commit()

    tutorial = Tutorial(title="Progress Tutorial", description="desc")
    db_session.add(tutorial)
    db_session.commit()
    exercise_one = Exercise(
        tutorial_id=tutorial.id,
        order_index=0,
        title="Exercise One",
        problem_markdown="p",
        entry_function="solve",
        test_cases=[],
    )
    exercise_two = Exercise(
        tutorial_id=tutorial.id,
        order_index=1,
        title="Exercise Two",
        problem_markdown="p",
        entry_function="solve",
        test_cases=[],
    )
    db_session.add(exercise_one)
    db_session.add(exercise_two)
    db_session.add(
        LeagueTutorial(league_id=league_a.id, tutorial_id=tutorial.id)
    )
    db_session.commit()

    alpha = Team(
        name="progress_alpha",
        school_name="School A",
        password_hash="test_hash",
        league_id=league_a.id,
        institution_id=institution.id,
    )
    beta = Team(
        name="progress_beta",
        school_name="School B",
        password_hash="test_hash",
        league_id=league_a.id,
        institution_id=institution.id,
    )
    gamma = Team(
        name="progress_gamma",
        school_name="School C",
        password_hash="test_hash",
        league_id=league_b.id,
        institution_id=institution.id,
    )
    for team in (alpha, beta, gamma):
        db_session.add(team)
    db_session.commit()
    for team in (alpha, beta, gamma):
        db_session.refresh(team)

    # Agent submissions for alpha: two validated (one with a hint), one failed
    now = utc_now()
    add_submission(
        db_session,
        code="agent v1",
        timestamp=now - timedelta(minutes=5),
        team_id=alpha.id,
        league_id=league_a.id,
    )
    add_submission(
        db_session,
        code="agent v2",
        timestamp=now,
        team_id=alpha.id,
        league_id=league_a.id,
        hint_included=True,
    )
    add_failed_submission(
        db_session,
        timestamp=now - timedelta(minutes=2),
        team_id=alpha.id,
        league_id=league_a.id,
    )

    # Ranked submissions for alpha. The rank-1 run is alpha's oldest ranked
    # submission, so it falls outside the last-3 window but must still set
    # achieved_first; the unranked v1/v2 above (pre-ranking rows) are newer
    # than some of these yet never appear in recent_rankings.
    for minutes_ago, ranking in ((4, 1), (3, 4), (1.5, 3), (0.5, 2)):
        add_submission(
            db_session,
            code=f"ranked agent ({ranking})",
            timestamp=now - timedelta(minutes=minutes_ago),
            team_id=alpha.id,
            league_id=league_a.id,
            ranking=ranking,
        )

    # Beta: a single ranked submission, never first
    add_submission(
        db_session,
        code="beta agent",
        timestamp=now - timedelta(minutes=1),
        team_id=beta.id,
        league_id=league_a.id,
        ranking=2,
    )

    # Exercise one: alpha fails then passes; beta's attempt never ran; gamma
    # passes but is in a league without the tutorial, so it must not count.
    add_exercise_attempt(db_session, alpha.id, exercise_one.id, passed=False)
    add_exercise_attempt(db_session, alpha.id, exercise_one.id, passed=True)
    add_exercise_attempt(db_session, beta.id, exercise_one.id)
    add_exercise_attempt(db_session, gamma.id, exercise_one.id, passed=True)
    db_session.commit()

    token = create_access_token(
        data={
            "sub": institution.name,
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(minutes=30),
    )
    return SimpleNamespace(
        institution=institution,
        tutorial=tutorial,
        exercises=(exercise_one, exercise_two),
        teams=(alpha, beta, gamma),
        headers={"Authorization": f"Bearer {token}"},
    )


def test_team_progress_success(client, progress_setup):
    response = client.get(
        "/institution/team-progress", headers=progress_setup.headers
    )
    assert response.status_code == 200
    data = response.json()

    # Only this institution's teams appear (the seed data has others)
    teams = {team["name"]: team for team in data["teams"]}
    assert set(teams) == {"progress_alpha", "progress_beta", "progress_gamma"}

    alpha = teams["progress_alpha"]
    assert alpha["league"] == "progress_league_a"
    assert alpha["school"] == "School A"
    assert alpha["total_attempts"] == 7
    assert alpha["validated_submissions"] == 6
    assert alpha["hints_used"] == 1
    assert alpha["latest_submission"] is not None
    # Last 3 ranked submissions oldest -> newest; unranked rows are skipped
    # and the older rank-1 run is outside the window but still sets the flag.
    assert alpha["recent_rankings"] == [4, 3, 2]
    assert alpha["achieved_first"] is True

    beta = teams["progress_beta"]
    assert beta["total_attempts"] == 1
    assert beta["validated_submissions"] == 1
    assert beta["recent_rankings"] == [2]
    assert beta["achieved_first"] is False

    gamma = teams["progress_gamma"]
    assert gamma["total_attempts"] == 0
    assert gamma["validated_submissions"] == 0
    assert gamma["hints_used"] == 0
    assert gamma["latest_submission"] is None
    assert gamma["recent_rankings"] == []
    assert gamma["achieved_first"] is False

    # One tutorial, scoped to league_a's two teams
    assert len(data["tutorials"]) == 1
    tutorial = data["tutorials"][0]
    assert tutorial["id"] == progress_setup.tutorial.id
    assert tutorial["title"] == "Progress Tutorial"
    assert tutorial["team_count"] == 2
    assert tutorial["league_names"] == ["progress_league_a"]

    exercise_one, exercise_two = progress_setup.exercises
    exercises = tutorial["exercises"]
    assert [e["id"] for e in exercises] == [exercise_one.id, exercise_two.id]
    # alpha ran, beta's attempt is metadata-only, gamma is out of scope
    assert exercises[0]["attempted_count"] == 2
    assert exercises[0]["passed_count"] == 1
    assert exercises[1]["attempted_count"] == 0
    assert exercises[1]["passed_count"] == 0


def test_team_progress_empty_institution(client, institution_headers):
    """A fresh institution with no leagues or teams gets empty sections."""
    response = client.get(
        "/institution/team-progress", headers=institution_headers
    )
    assert response.status_code == 200
    assert response.json() == {"teams": [], "tutorials": []}


def test_team_progress_admin_sees_own_institution(
    client, auth_headers, progress_setup
):
    """Admin tokens resolve to institution 1, not to other institutions."""
    response = client.get("/institution/team-progress", headers=auth_headers)
    assert response.status_code == 200
    team_names = {team["name"] for team in response.json()["teams"]}
    assert "progress_alpha" not in team_names


def test_team_progress_access_control(client, team_headers, progress_setup):
    # No token
    response = client.get("/institution/team-progress")
    assert response.status_code == 401

    # Team tokens are rejected
    response = client.get("/institution/team-progress", headers=team_headers)
    assert response.status_code == 403

    # Institution token without an institution id
    incomplete_token = create_access_token(
        data={"sub": "progress_institution", "role": "institution"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.get(
        "/institution/team-progress",
        headers={"Authorization": f"Bearer {incomplete_token}"},
    )
    assert response.status_code == 400
