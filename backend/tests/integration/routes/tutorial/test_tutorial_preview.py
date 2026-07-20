"""POST /tutorial/preview/submit-exercise: institution/teacher/admin accounts
run tutorial exercises as a fresh student would, with nothing persisted."""

import pytest
from sqlmodel import Session, select, func

from backend.database.db_models import (
    Exercise,
    ExerciseSubmission,
    ExerciseSubmissionMetadata,
    Tutorial,
)

WORD_COUNTER_TEST_CODE = '''\
def test_counts_each_word_once():
    """counts each word once"""
    check(count_words("the cat sat"), {"the": 1, "cat": 1, "sat": 1})
'''

PASSING_CODE = """
def count_words(sentence):
    counts = {}
    for word in sentence.split():
        counts[word] = counts.get(word, 0) + 1
    return counts
"""

FAILING_CODE = """
def count_words(sentence):
    return {}
"""

BROKEN_CODE = "def count_words(sentence:\n"


@pytest.fixture
def preview_exercise(db_session: Session) -> Exercise:
    """An exercise NOT attached to any league: preview must work on the whole
    library, unlike student submission which is league-scoped."""
    tutorial = Tutorial(title="Preview Test Tutorial")
    db_session.add(tutorial)
    db_session.flush()
    exercise = Exercise(
        tutorial_id=tutorial.id,
        order_index=0,
        title="Preview Word Counter",
        problem_markdown="Count the words",
        starter_code="def count_words(sentence):\n    pass\n",
        entry_function="count_words",
        test_code=WORD_COUNTER_TEST_CODE,
    )
    db_session.add(exercise)
    db_session.commit()
    db_session.refresh(exercise)
    return exercise


def _submission_row_counts(db_session: Session) -> tuple:
    subs = db_session.exec(select(func.count(ExerciseSubmission.id))).one()
    meta = db_session.exec(
        select(func.count(ExerciseSubmissionMetadata.id))
    ).one()
    return subs, meta


def test_preview_run_writes_nothing(
    client, db_session, institution_headers, preview_exercise, celery_workers
):
    before = _submission_row_counts(db_session)

    # Passing run
    response = client.post(
        "/tutorial/preview/submit-exercise",
        json={"exercise_id": preview_exercise.id, "code": PASSING_CODE},
        headers=institution_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is True
    assert data["submission_id"] is None
    assert len(data["test_results"]) == 1

    # Failing tests are still a 200 with per-test results
    response = client.post(
        "/tutorial/preview/submit-exercise",
        json={"exercise_id": preview_exercise.id, "code": FAILING_CODE},
        headers=institution_headers,
    )
    assert response.status_code == 200
    assert response.json()["passed"] is False

    # Broken code is a 400, and unlike /submit-exercise no failed attempt
    # is recorded
    response = client.post(
        "/tutorial/preview/submit-exercise",
        json={"exercise_id": preview_exercise.id, "code": BROKEN_CODE},
        headers=institution_headers,
    )
    assert response.status_code == 400

    # The whole point: no submission or metadata rows from any outcome
    assert _submission_row_counts(db_session) == before


def test_preview_run_admin_allowed(
    client, auth_headers, preview_exercise, celery_workers
):
    response = client.post(
        "/tutorial/preview/submit-exercise",
        json={"exercise_id": preview_exercise.id, "code": PASSING_CODE},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["passed"] is True


def test_preview_run_auth(client, team_headers, preview_exercise):
    # Student/team tokens must use /submit-exercise (which records attempts)
    response = client.post(
        "/tutorial/preview/submit-exercise",
        json={"exercise_id": preview_exercise.id, "code": PASSING_CODE},
        headers=team_headers,
    )
    assert response.status_code == 403

    # Unauthenticated
    response = client.post(
        "/tutorial/preview/submit-exercise",
        json={"exercise_id": preview_exercise.id, "code": PASSING_CODE},
    )
    assert response.status_code == 401


def test_preview_unknown_exercise(client, institution_headers):
    response = client.post(
        "/tutorial/preview/submit-exercise",
        json={"exercise_id": 99999, "code": PASSING_CODE},
        headers=institution_headers,
    )
    assert response.status_code == 404
