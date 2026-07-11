from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    Exercise,
    ExerciseSubmission,
    ExerciseSubmissionMetadata,
    Team,
    Tutorial,
)
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now

TEST_CASES = [
    {
        "name": "counts each word once",
        "args": ["the cat sat"],
        "expected": {"the": 1, "cat": 1, "sat": 1},
    },
    {
        "name": "counts repeated words",
        "args": ["the cat and the dog"],
        "expected": {"the": 2, "cat": 1, "and": 1, "dog": 1},
    },
    {
        "name": "empty string has no words",
        "args": [""],
        "expected": {},
    },
]

PASSING_CODE = """
def count_words(sentence):
    counts = {}
    for word in sentence.split():
        counts[word] = counts.get(word, 0) + 1
    return counts
"""

# Returns 1 for every word: fails only the repeated-words case.
PARTIAL_CODE = """
def count_words(sentence):
    counts = {}
    for word in sentence.split():
        counts[word] = 1
    return counts
"""


@pytest.fixture
def tutorial_with_exercise(db_session: Session) -> Tutorial:
    """One tutorial holding two exercises (to check ordering)."""
    tutorial = Tutorial(
        title="Test Tutorial",
        description="Tutorial used by the router tests",
    )
    db_session.add(tutorial)
    db_session.flush()

    # Inserted out of order on purpose: order_index must drive the ordering.
    later = Exercise(
        tutorial_id=tutorial.id,
        order_index=1,
        title="Second Exercise",
        problem_markdown="Second problem",
        starter_code="def second():\n    pass\n",
        entry_function="second",
        test_cases=[{"name": "returns none", "args": [], "expected": None}],
    )
    first = Exercise(
        tutorial_id=tutorial.id,
        order_index=0,
        title="Word Counter",
        problem_markdown="Count the words",
        starter_code="def count_words(sentence):\n    pass\n",
        entry_function="count_words",
        test_cases=TEST_CASES,
    )
    db_session.add(later)
    db_session.add(first)
    db_session.commit()
    db_session.refresh(tutorial)
    return tutorial


@pytest.fixture
def word_counter_exercise(
    db_session: Session, tutorial_with_exercise: Tutorial
) -> Exercise:
    return db_session.exec(
        select(Exercise).where(Exercise.title == "Word Counter")
    ).one()


def test_get_tutorials(client, team_headers, tutorial_with_exercise):
    response = client.get("/tutorial/tutorials", headers=team_headers)
    assert response.status_code == 200
    tutorials = response.json()["tutorials"]
    assert len(tutorials) == 1
    assert tutorials[0]["title"] == "Test Tutorial"
    assert tutorials[0]["exercise_count"] == 2

    # Unauthenticated access is rejected
    response = client.get("/tutorial/tutorials")
    assert response.status_code == 401


def test_get_tutorial_detail(client, team_headers, tutorial_with_exercise):
    response = client.get(
        f"/tutorial/tutorial/{tutorial_with_exercise.id}", headers=team_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Tutorial"

    # Exercises come back in order_index order regardless of insert order
    titles = [e["title"] for e in data["exercises"]]
    assert titles == ["Word Counter", "Second Exercise"]

    # The student sees the problem, not the test definitions
    exercise = data["exercises"][0]
    assert exercise["problem_markdown"] == "Count the words"
    assert exercise["starter_code"].startswith("def count_words")
    assert "test_cases" not in exercise
    assert "entry_function" not in exercise

    response = client.get("/tutorial/tutorial/99999", headers=team_headers)
    assert response.status_code == 404


def test_submit_exercise_all_tests_pass(
    client, db_session, team_headers, word_counter_exercise, celery_workers
):
    response = client.post(
        "/tutorial/submit-exercise",
        json={"exercise_id": word_counter_exercise.id, "code": PASSING_CODE},
        headers=team_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is True
    assert len(data["test_results"]) == len(TEST_CASES)
    assert all(t["passed"] for t in data["test_results"])

    # The code row is stored and linked to a metadata row
    submission = db_session.exec(
        select(ExerciseSubmission).where(
            ExerciseSubmission.id == data["submission_id"]
        )
    ).one()
    assert submission.code == PASSING_CODE
    assert submission.passed is True
    assert submission.meta.exercise_id == word_counter_exercise.id


def test_submit_exercise_failing_tests_still_stored(
    client, db_session, team_headers, word_counter_exercise, celery_workers
):
    """Failing test cases are a 200 with per-test results, and the code is
    stored so 'Last Submission' restores work in progress."""
    response = client.post(
        "/tutorial/submit-exercise",
        json={"exercise_id": word_counter_exercise.id, "code": PARTIAL_CODE},
        headers=team_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is False

    by_name = {t["name"]: t for t in data["test_results"]}
    assert by_name["counts each word once"]["passed"] is True
    assert by_name["empty string has no words"]["passed"] is True
    failed = by_name["counts repeated words"]
    assert failed["passed"] is False
    assert failed["expected"] == {"the": 2, "cat": 1, "and": 1, "dog": 1}
    assert "'the': 1" in failed["actual"]

    # Latest-submission returns the failing code for resumption
    response = client.get(
        f"/tutorial/exercise/{word_counter_exercise.id}/latest-submission",
        headers=team_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == PARTIAL_CODE
    assert data["passed"] is False


def test_submit_exercise_unsafe_code(
    client, db_session, team_headers, word_counter_exercise
):
    """Unsafe code is rejected by the AST check before any worker runs it:
    a metadata row is recorded but no code is stored."""
    response = client.post(
        "/tutorial/submit-exercise",
        json={
            "exercise_id": word_counter_exercise.id,
            "code": "import os\n\ndef count_words(sentence):\n    return {}\n",
        },
        headers=team_headers,
    )
    assert response.status_code == 400
    assert "Code is not safe" in response.json()["detail"]

    metas = db_session.exec(select(ExerciseSubmissionMetadata)).all()
    assert len(metas) == 1
    assert metas[0].submission is None


def test_submit_exercise_error_paths(
    client, team_headers, word_counter_exercise, celery_workers
):
    # Syntax error: caught by the AST check in the API before any worker runs
    response = client.post(
        "/tutorial/submit-exercise",
        json={
            "exercise_id": word_counter_exercise.id,
            "code": "def count_words(sentence)\n    return {}\n",
        },
        headers=team_headers,
    )
    assert response.status_code == 400
    assert "Syntax error" in response.json()["detail"]

    # Code that parses but blows up when executed (before any test runs)
    response = client.post(
        "/tutorial/submit-exercise",
        json={
            "exercise_id": word_counter_exercise.id,
            "code": "raise RuntimeError('boom')\n",
        },
        headers=team_headers,
    )
    assert response.status_code == 400
    assert "failed to run" in response.json()["detail"]

    # Missing entry function
    response = client.post(
        "/tutorial/submit-exercise",
        json={
            "exercise_id": word_counter_exercise.id,
            "code": "def wrong_name(sentence):\n    return {}\n",
        },
        headers=team_headers,
    )
    assert response.status_code == 400
    assert "count_words" in response.json()["detail"]

    # Unknown exercise
    response = client.post(
        "/tutorial/submit-exercise",
        json={"exercise_id": 99999, "code": PASSING_CODE},
        headers=team_headers,
    )
    assert response.status_code == 404


def test_submit_exercise_timeout(
    client, team_headers, word_counter_exercise, celery_workers
):
    """An infinite loop is killed by the worker time limit and reported as a
    timeout failure (the test compose shortens the limit to 2s)."""
    response = client.post(
        "/tutorial/submit-exercise",
        json={
            "exercise_id": word_counter_exercise.id,
            "code": (
                "def count_words(sentence):\n"
                "    while True:\n"
                "        pass\n"
            ),
        },
        headers=team_headers,
    )
    assert response.status_code == 400
    assert "too much time" in response.json()["detail"]


def test_submit_exercise_auth(client, word_counter_exercise, auth_headers):
    # No token
    response = client.post(
        "/tutorial/submit-exercise",
        json={"exercise_id": word_counter_exercise.id, "code": PASSING_CODE},
    )
    assert response.status_code == 401

    # Admin tokens are not team tokens
    response = client.post(
        "/tutorial/submit-exercise",
        json={"exercise_id": word_counter_exercise.id, "code": PASSING_CODE},
        headers=auth_headers,
    )
    assert response.status_code == 403

    # Student token without a team_id
    teamless_token = create_access_token(
        data={"sub": "no_team_student", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/tutorial/submit-exercise",
        json={"exercise_id": word_counter_exercise.id, "code": PASSING_CODE},
        headers={"Authorization": f"Bearer {teamless_token}"},
    )
    assert response.status_code == 400
    assert "team token" in response.json()["detail"]


def test_submit_exercise_rate_limit(
    client, db_session, team_headers, word_counter_exercise
):
    """The 6th attempt inside a minute is rejected before any code runs."""
    team = db_session.exec(select(Team).where(Team.name == "TeamA")).one()
    now = utc_now()
    for _ in range(5):
        db_session.add(
            ExerciseSubmissionMetadata(
                team_id=team.id,
                exercise_id=word_counter_exercise.id,
                timestamp=now,
            )
        )
    db_session.commit()

    response = client.post(
        "/tutorial/submit-exercise",
        json={"exercise_id": word_counter_exercise.id, "code": PASSING_CODE},
        headers=team_headers,
    )
    assert response.status_code == 429
    assert "per minute" in response.json()["detail"]


def test_exercise_submission_history(
    client, db_session, team_headers, word_counter_exercise
):
    """History lists the team's stored attempts for the exercise, newest first."""
    team = db_session.exec(select(Team).where(Team.name == "TeamA")).one()

    # Empty state
    response = client.get(
        f"/tutorial/exercise/{word_counter_exercise.id}/submissions",
        headers=team_headers,
    )
    assert response.status_code == 200
    assert response.json()["submissions"] == []

    response = client.get(
        f"/tutorial/exercise/{word_counter_exercise.id}/latest-submission",
        headers=team_headers,
    )
    assert response.status_code == 200
    assert response.json()["code"] is None

    base = utc_now()
    for i, (code, passed) in enumerate([("old code", False), ("new code", True)]):
        meta = ExerciseSubmissionMetadata(
            team_id=team.id,
            exercise_id=word_counter_exercise.id,
            timestamp=base + timedelta(minutes=i - 10),
        )
        db_session.add(meta)
        db_session.flush()
        db_session.add(
            ExerciseSubmission(
                code=code,
                timestamp=base + timedelta(minutes=i - 10),
                passed=passed,
                test_results=[],
                metadata_id=meta.id,
            )
        )
    db_session.commit()

    response = client.get(
        f"/tutorial/exercise/{word_counter_exercise.id}/submissions",
        headers=team_headers,
    )
    assert response.status_code == 200
    submissions = response.json()["submissions"]
    assert [s["code"] for s in submissions] == ["new code", "old code"]
    assert submissions[0]["passed"] is True

    response = client.get(
        f"/tutorial/exercise/{word_counter_exercise.id}/latest-submission",
        headers=team_headers,
    )
    assert response.json()["code"] == "new code"

    # History for a missing exercise 404s
    response = client.get(
        "/tutorial/exercise/99999/submissions", headers=team_headers
    )
    assert response.status_code == 404
