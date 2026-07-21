"""Shared fixture for the classroom workspace endpoints
(/institution/classroom/* and /institution/student/*)."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlmodel import Session

from backend.database.db_models import (
    Exercise,
    League,
    LeagueTutorial,
    Team,
    Tutorial,
)
from backend.routes.auth.auth_core import create_access_token
from backend.tests.conftest import (
    add_exercise_attempt,
    add_failed_submission,
    add_submission,
    create_test_institution,
)
from backend.time_utils import utc_now


def _institution_token(institution) -> dict:
    token = create_access_token(
        data={
            "sub": institution.name,
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def classroom_setup(db_session: Session) -> SimpleNamespace:
    """Two institutions. The owner has classroom_9a (tutorial one attached,
    students adam + zoe) and classroom_9b (tutorial two attached, student
    misha). The rival institution has its own league and student.

    adam: agent history with rankings 1,4,3,2 (oldest->newest) plus one
    unranked validated run with a hint and one failed attempt; fails then
    passes exercise one; also attempts tutorial-two's exercise (out of 9a's
    scope) with the NEWEST timestamp of all his activity, so last_active must
    come from exercise activity while 9a's exercise counts exclude it.
    zoe: no agent submissions; one metadata-only attempt on exercise one.
    """
    owner = create_test_institution(
        db_session, name="classroom_owner", password_hash="test_hash"
    )
    rival = create_test_institution(
        db_session, name="classroom_rival", password_hash="test_hash"
    )

    league_a = League(
        name="classroom_9a",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=owner.id,
    )
    league_b = League(
        name="classroom_9b",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=owner.id,
    )
    rival_league = League(
        name="classroom_rival_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=rival.id,
    )
    for league in (league_a, league_b, rival_league):
        db_session.add(league)
    db_session.commit()

    tutorial_one = Tutorial(title="Classroom Tutorial One", description="d")
    tutorial_two = Tutorial(title="Classroom Tutorial Two", description="d")
    db_session.add(tutorial_one)
    db_session.add(tutorial_two)
    db_session.commit()
    exercise_one = Exercise(
        tutorial_id=tutorial_one.id,
        order_index=0,
        title="Exercise One",
        problem_markdown="p",
        entry_function="solve",
    )
    exercise_two = Exercise(
        tutorial_id=tutorial_one.id,
        order_index=1,
        title="Exercise Two",
        problem_markdown="p",
        entry_function="solve",
    )
    exercise_other = Exercise(
        tutorial_id=tutorial_two.id,
        order_index=0,
        title="Other Tutorial Exercise",
        problem_markdown="p",
        entry_function="solve",
    )
    for exercise in (exercise_one, exercise_two, exercise_other):
        db_session.add(exercise)
    db_session.add(
        LeagueTutorial(league_id=league_a.id, tutorial_id=tutorial_one.id)
    )
    db_session.add(
        LeagueTutorial(league_id=league_b.id, tutorial_id=tutorial_two.id)
    )
    db_session.commit()

    # "zoe" sorts after "adam": row order must be name-based, not id-based.
    zoe = Team(
        name="zoe",
        school_name="Greenfield High",
        password_hash="test_hash",
        league_id=league_a.id,
        institution_id=owner.id,
    )
    adam = Team(
        name="adam",
        school_name="Greenfield High",
        password_hash="test_hash",
        league_id=league_a.id,
        institution_id=owner.id,
    )
    misha = Team(
        name="misha",
        school_name="Greenfield High",
        password_hash="test_hash",
        league_id=league_b.id,
        institution_id=owner.id,
    )
    rival_team = Team(
        name="rival_student",
        school_name="Rival High",
        password_hash="test_hash",
        league_id=rival_league.id,
        institution_id=rival.id,
    )
    for team in (zoe, adam, misha, rival_team):
        db_session.add(team)
    db_session.commit()
    for team in (zoe, adam, misha, rival_team):
        db_session.refresh(team)

    now = utc_now()
    # Ranked agent history for adam, oldest -> newest: 1, 4, 3, 2.
    for minutes_ago, ranking in ((40, 1), (30, 4), (20, 3), (10, 2)):
        add_submission(
            db_session,
            code=f"ranked agent ({ranking})",
            timestamp=now - timedelta(minutes=minutes_ago),
            team_id=adam.id,
            league_id=league_a.id,
            ranking=ranking,
        )
    add_submission(
        db_session,
        code="hinted agent",
        timestamp=now - timedelta(minutes=5),
        team_id=adam.id,
        league_id=league_a.id,
        hint_included=True,
        duration_ms=321.0,
    )
    add_failed_submission(
        db_session,
        timestamp=now - timedelta(minutes=4),
        team_id=adam.id,
        league_id=league_a.id,
    )

    # Exercise one: adam fails then passes; zoe's attempt never ran.
    add_exercise_attempt(
        db_session,
        adam.id,
        exercise_one.id,
        passed=False,
        timestamp=now - timedelta(minutes=3),
        code="def solve(): return 0",
        test_results=[{"name": "test_basic", "passed": False}],
    )
    add_exercise_attempt(
        db_session,
        adam.id,
        exercise_one.id,
        passed=True,
        timestamp=now - timedelta(minutes=2),
        code="def solve(): return 1",
        test_results=[{"name": "test_basic", "passed": True}],
    )
    add_exercise_attempt(
        db_session, zoe.id, exercise_one.id, timestamp=now - timedelta(minutes=6)
    )
    # Out-of-classroom activity: newest of all adam's activity.
    add_exercise_attempt(
        db_session,
        adam.id,
        exercise_other.id,
        passed=True,
        timestamp=now - timedelta(minutes=1),
    )
    db_session.commit()

    return SimpleNamespace(
        owner=owner,
        rival=rival,
        league_a=league_a,
        league_b=league_b,
        rival_league=rival_league,
        tutorial_one=tutorial_one,
        tutorial_two=tutorial_two,
        exercises=(exercise_one, exercise_two, exercise_other),
        adam=adam,
        zoe=zoe,
        misha=misha,
        rival_team=rival_team,
        owner_headers=_institution_token(owner),
        rival_headers=_institution_token(rival),
        now=now,
    )
