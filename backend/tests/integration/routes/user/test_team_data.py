"""Tests for GET /user/team-data — the student landing page's single fetch."""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    Exercise,
    ExerciseSubmission,
    ExerciseSubmissionMetadata,
    League,
    LeagueTutorial,
    Submission,
    SubmissionMetadata,
    Team,
    Tutorial,
)
from backend.routes.auth.auth_db import mint_team_token
from backend.tests.conftest import build_institution
from backend.time_utils import utc_now


@pytest.fixture
def classroom_fixture(db_session: Session) -> dict:
    """A teacher institution with a classroom league, one enrolled student,
    two attached tutorials, and mixed exercise/agent progress."""
    now = utc_now()

    institution = build_institution(
        name="Team Data Classroom School",
        contact_person="Teacher",
        contact_email="teacher@teamdata.com",
        created_date=now,
        subscription_active=True,
        subscription_expiry=now + timedelta(days=30),
        password_hash="hash",
        is_teacher=True,
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    league = League(
        name="team_data_classroom",
        created_date=now,
        expiry_date=now + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    team = Team(
        name="team_data_student",
        school_name="Team Data School",
        password_hash="hash",
        league_id=league.id,
        institution_id=institution.id,
    )
    db_session.add(team)

    tutorial_one = Tutorial(title="Team Data Basics", description="Loops")
    tutorial_two = Tutorial(title="Team Data Advanced", description="Dicts")
    db_session.add(tutorial_one)
    db_session.add(tutorial_two)
    db_session.commit()

    exercises = []
    for tutorial, count in ((tutorial_one, 2), (tutorial_two, 1)):
        db_session.add(
            LeagueTutorial(league_id=league.id, tutorial_id=tutorial.id)
        )
        for index in range(count):
            exercise = Exercise(
                tutorial_id=tutorial.id,
                order_index=index,
                title=f"{tutorial.title} ex{index}",
                problem_markdown="Do the thing",
                entry_function="solve",
            )
            db_session.add(exercise)
            exercises.append(exercise)
    db_session.commit()
    for exercise in exercises:
        db_session.refresh(exercise)
    db_session.refresh(team)

    return {
        "institution": institution,
        "league": league,
        "team": team,
        "tutorial_one": tutorial_one,
        "tutorial_two": tutorial_two,
        "exercises": exercises,
    }


def _add_exercise_attempt(
    db_session: Session, team_id: int, exercise_id: int, passed: bool | None
) -> None:
    """passed=None records a failed-to-run attempt (metadata only)."""
    meta = ExerciseSubmissionMetadata(
        team_id=team_id, exercise_id=exercise_id, timestamp=utc_now()
    )
    db_session.add(meta)
    db_session.flush()
    if passed is not None:
        db_session.add(
            ExerciseSubmission(
                code="def solve(): pass",
                timestamp=utc_now(),
                passed=passed,
                test_results=[],
                metadata_id=meta.id,
            )
        )
    db_session.commit()


def _add_agent_attempt(
    db_session: Session,
    team_id: int,
    league_id: int,
    ranking: int | None = None,
    validated: bool = True,
) -> None:
    meta = SubmissionMetadata(
        team_id=team_id, league_id=league_id, timestamp=utc_now()
    )
    db_session.add(meta)
    db_session.flush()
    if validated:
        db_session.add(
            Submission(
                code="class CustomPlayer: pass",
                timestamp=utc_now(),
                ranking=ranking,
                metadata_id=meta.id,
            )
        )
    db_session.commit()


def test_team_data_classroom_full_payload(client, db_session, classroom_fixture):
    fix = classroom_fixture
    team = fix["team"]
    ex_one_a, ex_one_b, ex_two_a = fix["exercises"]

    # Tutorial one: first exercise passed (after a failed run), second only
    # attempted. Tutorial two: untouched.
    _add_exercise_attempt(db_session, team.id, ex_one_a.id, passed=False)
    _add_exercise_attempt(db_session, team.id, ex_one_a.id, passed=True)
    _add_exercise_attempt(db_session, team.id, ex_one_b.id, passed=None)

    # Agent game: one failed validation, then ranked submissions 1st -> 3rd.
    _add_agent_attempt(db_session, team.id, fix["league"].id, validated=False)
    _add_agent_attempt(db_session, team.id, fix["league"].id, ranking=1)
    _add_agent_attempt(db_session, team.id, fix["league"].id, ranking=3)

    token = mint_team_token(team)
    resp = client.get(
        "/user/team-data", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.json()
    data = resp.json()

    assert data["team_name"] == "team_data_student"
    assert data["is_classroom"] is True
    assert data["institution_name"] == "Team Data Classroom School"
    assert data["is_demo"] is False
    assert data["league"] == {
        "id": fix["league"].id,
        "name": "team_data_classroom",
        "game": "greedy_pig",
    }

    tutorials = {t["title"]: t for t in data["tutorials"]}
    assert tutorials["Team Data Basics"] == {
        "id": fix["tutorial_one"].id,
        "title": "Team Data Basics",
        "description": "Loops",
        "exercise_count": 2,
        "attempted_count": 2,
        "passed_count": 1,
    }
    assert tutorials["Team Data Advanced"]["exercise_count"] == 1
    assert tutorials["Team Data Advanced"]["attempted_count"] == 0
    assert tutorials["Team Data Advanced"]["passed_count"] == 0

    agent = data["agent_game"]
    assert agent["total_attempts"] == 3
    assert agent["validated_submissions"] == 2
    assert agent["recent_rankings"] == [1, 3]  # oldest -> newest
    assert agent["achieved_first"] is True
    assert agent["latest_submission"] is not None


def test_team_data_competition_institution(client, db_session):
    """A non-teacher institution's student reads as competition wording."""
    league = db_session.exec(
        select(League).where(League.name == "greedy_pig_league")
    ).first()
    team = db_session.exec(select(Team).where(Team.name == "TeamA")).first()
    team.league_id = league.id
    db_session.commit()
    db_session.refresh(team)

    token = mint_team_token(team)
    resp = client.get(
        "/user/team-data", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_classroom"] is False
    assert data["institution_name"] == "Admin Institution"
    assert data["league"]["name"] == "greedy_pig_league"
    assert data["tutorials"] == []
    assert data["agent_game"]["total_attempts"] == 0
    assert data["agent_game"]["validated_submissions"] == 0
    assert data["agent_game"]["recent_rankings"] == []
    assert data["agent_game"]["achieved_first"] is False
    assert data["agent_game"]["latest_submission"] is None


def test_team_data_unassigned_team(client, db_session):
    """Unassigned teams get league=None so the frontend routes to the picker."""
    team = db_session.exec(select(Team).where(Team.name == "TeamB")).first()
    assert team.league.name == "unassigned"

    token = mint_team_token(team)
    resp = client.get(
        "/user/team-data", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["league"] is None
    assert data["tutorials"] == []
    assert data["agent_game"] is None


def test_team_data_stats_scoped_to_current_league(
    client, db_session, classroom_fixture
):
    """Attempts made in a previous league don't leak into the current one."""
    fix = classroom_fixture
    team = fix["team"]

    other_league = League(
        name="team_data_other_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=fix["institution"].id,
    )
    db_session.add(other_league)
    db_session.commit()
    db_session.refresh(other_league)

    _add_agent_attempt(db_session, team.id, other_league.id, ranking=1)
    _add_agent_attempt(db_session, team.id, fix["league"].id, ranking=2)

    token = mint_team_token(team)
    resp = client.get(
        "/user/team-data", headers={"Authorization": f"Bearer {token}"}
    )
    agent = resp.json()["agent_game"]
    assert agent["total_attempts"] == 1
    assert agent["recent_rankings"] == [2]
    assert agent["achieved_first"] is False


def test_team_data_rejects_non_team_tokens(client, auth_headers):
    """Admin tokens fail the student-role gate before any team lookup."""
    resp = client.get("/user/team-data", headers=auth_headers)
    assert resp.status_code == 403


def test_team_data_requires_auth(client):
    resp = client.get("/user/team-data")
    assert resp.status_code in (401, 403)
