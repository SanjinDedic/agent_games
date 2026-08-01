"""Integration tests for /tutorial/submit-exercise-result.

The endpoint persists exercise attempts the browser already executed via
Pyodide (frontend/src/pyodide/exercise_harness.py). No server-side
execution is involved anywhere in this file — that is the point of the
endpoint.
"""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    Exercise,
    ExerciseSubmission,
    ExerciseSubmissionMetadata,
    LeagueTutorial,
    Team,
    Tutorial,
)
from backend.fallback_lambda.executor import MAX_STDOUT_CHARS
from backend.time_utils import utc_now

PASSING_CODE = "def add(a, b):\n    return a + b\n"


def make_row(name="adds", passed=True, **overrides):
    row = {
        "name": name,
        "call": None,
        "expected": 3,
        "actual": "3",
        "passed": passed,
        "error": None,
    }
    row.update(overrides)
    return row


def make_payload(exercise_id, **overrides):
    payload = {
        "exercise_id": exercise_id,
        "code": PASSING_CODE,
        "status": "success",
        "passed": True,
        "test_results": [make_row()],
        "stdout": None,
        "duration_ms": 1.5,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def pyodide_exercise(db_session: Session) -> Exercise:
    """One exercise in a tutorial attached to TeamA's league."""
    tutorial = Tutorial(
        title="Pyodide Tutorial",
        description="Tutorial used by the result-submission tests",
    )
    db_session.add(tutorial)
    db_session.flush()

    team_a = db_session.exec(select(Team).where(Team.name == "TeamA")).one()
    db_session.add(
        LeagueTutorial(league_id=team_a.league_id, tutorial_id=tutorial.id)
    )
    exercise = Exercise(
        tutorial_id=tutorial.id,
        order_index=0,
        title="Add",
        problem_markdown="Add two numbers",
        starter_code="def add(a, b):\n    pass\n",
        entry_function="add",
        test_code="def test_add():\n    check(add(1, 2), 3)\n",
    )
    db_session.add(exercise)
    db_session.commit()
    db_session.refresh(exercise)
    return exercise


def test_successful_result_is_stored_and_stamped(
    client, db_session, team_headers, pyodide_exercise
):
    response = client.post(
        "/tutorial/submit-exercise-result",
        json=make_payload(pyodide_exercise.id, stdout="hi\n"),
        headers=team_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is True
    assert data["exercise_id"] == pyodide_exercise.id
    assert data["stdout"] == "hi\n"
    assert data["duration_ms"] == 1.5
    assert all(row["source"] == "pyodide" for row in data["test_results"])

    # Stored exactly as echoed, linked to a metadata row like a worker run
    submission = db_session.exec(
        select(ExerciseSubmission).where(
            ExerciseSubmission.id == data["submission_id"]
        )
    ).one()
    assert submission.code == PASSING_CODE
    assert submission.passed is True
    assert submission.test_results == data["test_results"]
    assert submission.meta.exercise_id == pyodide_exercise.id

    # And the normal history endpoint serves it back
    response = client.get(
        f"/tutorial/exercise/{pyodide_exercise.id}/latest-submission",
        headers=team_headers,
    )
    assert response.json()["code"] == PASSING_CODE


def test_passed_is_recomputed_from_rows(
    client, db_session, team_headers, pyodide_exercise
):
    """A client claiming passed=True with a failing row can't inflate the
    stored outcome."""
    payload = make_payload(
        pyodide_exercise.id,
        passed=True,
        test_results=[make_row(), make_row(name="fails", passed=False)],
    )
    response = client.post(
        "/tutorial/submit-exercise-result",
        json=payload,
        headers=team_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is False

    submission = db_session.exec(
        select(ExerciseSubmission).where(
            ExerciseSubmission.id == data["submission_id"]
        )
    ).one()
    assert submission.passed is False


def test_rows_are_rebuilt_from_contract_keys(
    client, team_headers, pyodide_exercise
):
    """Unknown keys are dropped, passed is coerced to bool, and a
    client-sent source is overwritten. (Non-dict rows are already rejected
    by pydantic's List[dict] validation with a 422.)"""
    payload = make_payload(
        pyodide_exercise.id,
        test_results=[make_row(passed=1, source="celery", sneaky="ignored")],
    )
    response = client.post(
        "/tutorial/submit-exercise-result",
        json=payload,
        headers=team_headers,
    )
    assert response.status_code == 200
    (row,) = response.json()["test_results"]
    assert row == {
        "name": "adds",
        "call": None,
        "expected": 3,
        "actual": "3",
        "passed": True,
        "error": None,
        "source": "pyodide",
    }


def test_error_result_records_metadata_only(
    client, db_session, team_headers, pyodide_exercise
):
    """A status:"error" run mirrors the fallback 400 contract: detail + stdout,
    metadata row for progress/rate-limiting, no code stored."""
    payload = make_payload(
        pyodide_exercise.id,
        status="error",
        message="Your code failed to run before any tests started.",
        passed=False,
        test_results=[],
        stdout="partial print\n",
    )
    response = client.post(
        "/tutorial/submit-exercise-result",
        json=payload,
        headers=team_headers,
    )
    assert response.status_code == 400
    data = response.json()
    assert "failed to run" in data["detail"]
    assert data["stdout"] == "partial print\n"

    assert db_session.exec(select(ExerciseSubmission)).all() == []
    (meta,) = db_session.exec(select(ExerciseSubmissionMetadata)).all()
    assert meta.exercise_id == pyodide_exercise.id


def test_success_with_no_rows_is_an_error(
    client, db_session, team_headers, pyodide_exercise
):
    """No rows can never be a vacuous pass, same as the worker."""
    response = client.post(
        "/tutorial/submit-exercise-result",
        json=make_payload(pyodide_exercise.id, test_results=[]),
        headers=team_headers,
    )
    assert response.status_code == 400
    assert db_session.exec(select(ExerciseSubmission)).all() == []


def test_rate_limit_is_shared_with_submit_exercise(
    client, db_session, team_headers, pyodide_exercise
):
    """Both endpoints count the same ExerciseSubmissionMetadata budget, so
    a student can't double their 5/minute by mixing paths. (The 429 fires
    before any enqueue, so no worker is needed.)"""
    team_a = db_session.exec(select(Team).where(Team.name == "TeamA")).one()
    for _ in range(5):
        db_session.add(
            ExerciseSubmissionMetadata(
                team_id=team_a.id,
                exercise_id=pyodide_exercise.id,
                timestamp=utc_now(),
            )
        )
    db_session.commit()

    response = client.post(
        "/tutorial/submit-exercise-result",
        json=make_payload(pyodide_exercise.id),
        headers=team_headers,
    )
    assert response.status_code == 429

    response = client.post(
        "/tutorial/submit-exercise",
        json={"exercise_id": pyodide_exercise.id, "code": PASSING_CODE},
        headers=team_headers,
    )
    assert response.status_code == 429

    # Outside the window the budget resets
    for meta in db_session.exec(select(ExerciseSubmissionMetadata)).all():
        meta.timestamp = utc_now() - timedelta(minutes=2)
        db_session.add(meta)
    db_session.commit()

    response = client.post(
        "/tutorial/submit-exercise-result",
        json=make_payload(pyodide_exercise.id),
        headers=team_headers,
    )
    assert response.status_code == 200


def test_requires_student_role(client, admin_headers, pyodide_exercise):
    """Admin tokens are rejected by the role decorator, same as
    /submit-exercise."""
    response = client.post(
        "/tutorial/submit-exercise-result",
        json=make_payload(pyodide_exercise.id),
        headers=admin_headers,
    )
    assert response.status_code == 403


def test_exercise_outside_team_league_404s(
    client, db_session, team_headers, pyodide_exercise
):
    tutorial = Tutorial(title="Unattached", description="")
    db_session.add(tutorial)
    db_session.flush()
    other = Exercise(
        tutorial_id=tutorial.id,
        order_index=0,
        title="Hidden",
        problem_markdown="",
        starter_code="",
        entry_function="f",
        test_code="def test_f():\n    check(f(), None)\n",
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    response = client.post(
        "/tutorial/submit-exercise-result",
        json=make_payload(other.id),
        headers=team_headers,
    )
    assert response.status_code == 404


def test_stdout_is_truncated_server_side(
    client, team_headers, pyodide_exercise
):
    response = client.post(
        "/tutorial/submit-exercise-result",
        json=make_payload(pyodide_exercise.id, stdout="x" * (MAX_STDOUT_CHARS * 2)),
        headers=team_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["stdout"]) == MAX_STDOUT_CHARS
