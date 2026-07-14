"""Admin CRUD for tutorials and exercises (create/edit/delete/reorder)."""

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    Exercise,
    ExerciseSubmission,
    ExerciseSubmissionMetadata,
    Team,
    Tutorial,
)
from backend.time_utils import utc_now

EXERCISE_PAYLOAD = {
    "title": "Sum Two Numbers",
    "problem_markdown": "# Sum\n\nAdd the two numbers.",
    "starter_code": "def add(a, b):\n    pass\n",
    "entry_function": "add",
    "test_code": "def test_adds():\n    check(add(1, 2), 3)\n",
    "solution": "def add(a, b):\n    return a + b\n",
    # The blank hint must be dropped by validation
    "exercise_hints": ["Use `+`.", "   ", "Then `return` the result."],
}
EXPECTED_HINTS = ["Use `+`.", "Then `return` the result."]

SEEDED_TEST_CODE = "def test_runs():\n    check(f(), None)\n"


@pytest.fixture
def team(db_session: Session) -> Team:
    """TeamA from the seed data (same team team_headers builds its token for)."""
    return db_session.exec(select(Team).where(Team.name == "TeamA")).one()


@pytest.fixture
def tutorial(db_session: Session) -> Tutorial:
    tutorial = Tutorial(title="Admin CRUD Tutorial", description="Editable")
    db_session.add(tutorial)
    db_session.commit()
    db_session.refresh(tutorial)
    return tutorial


@pytest.fixture
def tutorial_with_exercises(db_session: Session, tutorial: Tutorial) -> Tutorial:
    for index, name in enumerate(["First", "Second", "Third"]):
        db_session.add(
            Exercise(
                tutorial_id=tutorial.id,
                order_index=index,
                title=name,
                problem_markdown=f"{name} problem",
                starter_code="def f():\n    pass\n",
                entry_function="f",
                test_code=SEEDED_TEST_CODE,
            )
        )
    db_session.commit()
    db_session.refresh(tutorial)
    return tutorial


def exercise_ids_in_order(db_session: Session, tutorial_id: int) -> list:
    return list(
        db_session.exec(
            select(Exercise.id)
            .where(Exercise.tutorial_id == tutorial_id)
            .order_by(Exercise.order_index)
        ).all()
    )


# -- tutorial CRUD ----------------------------------------------------------


def test_create_tutorial(client, auth_headers):
    response = client.post(
        "/tutorial/tutorials",
        json={"title": "New Tutorial", "description": "About things"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    created = response.json()
    assert created["title"] == "New Tutorial"

    listing = client.get("/tutorial/tutorials", headers=auth_headers).json()
    assert any(t["id"] == created["id"] for t in listing["tutorials"])


def test_create_tutorial_duplicate_title_conflicts(client, auth_headers, tutorial):
    response = client.post(
        "/tutorial/tutorials",
        json={"title": tutorial.title},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_create_tutorial_blank_title_rejected(client, auth_headers):
    response = client.post(
        "/tutorial/tutorials", json={"title": "   "}, headers=auth_headers
    )
    assert response.status_code == 422


def test_update_tutorial(client, auth_headers, tutorial):
    response = client.put(
        f"/tutorial/tutorial/{tutorial.id}",
        json={"title": "Renamed", "description": "New text"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": tutorial.id,
        "title": "Renamed",
        "description": "New text",
    }


def test_update_tutorial_keeps_own_title(client, auth_headers, tutorial):
    """Saving a tutorial without renaming it must not trip the dup check."""
    response = client.put(
        f"/tutorial/tutorial/{tutorial.id}",
        json={"title": tutorial.title, "description": "Updated only"},
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_delete_tutorial_removes_exercises_and_history(
    client, auth_headers, db_session, tutorial_with_exercises, team
):
    exercise_id = exercise_ids_in_order(db_session, tutorial_with_exercises.id)[0]
    meta = ExerciseSubmissionMetadata(
        team_id=team.id, exercise_id=exercise_id, timestamp=utc_now()
    )
    db_session.add(meta)
    db_session.flush()
    db_session.add(
        ExerciseSubmission(
            code="def f():\n    return None\n",
            timestamp=utc_now(),
            passed=True,
            test_results=[],
            metadata_id=meta.id,
        )
    )
    db_session.commit()

    response = client.delete(
        f"/tutorial/tutorial/{tutorial_with_exercises.id}", headers=auth_headers
    )
    assert response.status_code == 200

    db_session.expire_all()
    assert db_session.get(Tutorial, tutorial_with_exercises.id) is None
    assert db_session.exec(select(Exercise)).all() == []
    assert db_session.exec(select(ExerciseSubmissionMetadata)).all() == []
    assert db_session.exec(select(ExerciseSubmission)).all() == []


def test_delete_missing_tutorial_404(client, auth_headers):
    response = client.delete("/tutorial/tutorial/9999", headers=auth_headers)
    assert response.status_code == 404


# -- admin detail -----------------------------------------------------------


def test_admin_detail_includes_full_exercise_definition(
    client, auth_headers, tutorial_with_exercises
):
    response = client.get(
        f"/tutorial/admin/tutorial/{tutorial_with_exercises.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    detail = response.json()
    assert [e["title"] for e in detail["exercises"]] == [
        "First",
        "Second",
        "Third",
    ]
    first = detail["exercises"][0]
    assert first["entry_function"] == "f"
    # The admin editor needs the test script to show and run it
    assert first["test_code"] == SEEDED_TEST_CODE


def test_admin_detail_denied_for_team(client, team_headers, tutorial):
    response = client.get(
        f"/tutorial/admin/tutorial/{tutorial.id}", headers=team_headers
    )
    assert response.status_code == 403


# -- exercise CRUD ----------------------------------------------------------


def test_create_exercise_appends_at_end(
    client, auth_headers, db_session, tutorial_with_exercises
):
    response = client.post(
        f"/tutorial/tutorial/{tutorial_with_exercises.id}/exercises",
        json=EXERCISE_PAYLOAD,
        headers=auth_headers,
    )
    assert response.status_code == 200
    created = response.json()
    assert created["order_index"] == 3
    assert exercise_ids_in_order(db_session, tutorial_with_exercises.id)[-1] == (
        created["id"]
    )
    db_session.expire_all()
    exercise = db_session.get(Exercise, created["id"])
    assert exercise.test_code == EXERCISE_PAYLOAD["test_code"]
    assert exercise.solution == EXERCISE_PAYLOAD["solution"]
    assert exercise.exercise_hints == EXPECTED_HINTS


def test_create_exercise_blank_test_code_stored_as_null(
    client, auth_headers, db_session, tutorial
):
    """A whitespace-only script must not shadow the worker's loud
    'defines no tests' error with a vacuous pass; a blank solution is
    normalized the same way."""
    payload = {**EXERCISE_PAYLOAD, "test_code": "   \n", "solution": ""}
    response = client.post(
        f"/tutorial/tutorial/{tutorial.id}/exercises",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 200
    db_session.expire_all()
    exercise = db_session.get(Exercise, response.json()["id"])
    assert exercise.test_code is None
    assert exercise.solution is None


def test_create_exercise_rejects_bad_entry_function(client, auth_headers, tutorial):
    payload = {**EXERCISE_PAYLOAD, "entry_function": "not a name"}
    response = client.post(
        f"/tutorial/tutorial/{tutorial.id}/exercises",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_update_exercise_replaces_all_fields(
    client, auth_headers, db_session, tutorial_with_exercises
):
    exercise_id = exercise_ids_in_order(db_session, tutorial_with_exercises.id)[1]
    response = client.put(
        f"/tutorial/exercise/{exercise_id}",
        json=EXERCISE_PAYLOAD,
        headers=auth_headers,
    )
    assert response.status_code == 200

    db_session.expire_all()
    exercise = db_session.get(Exercise, exercise_id)
    assert exercise.title == "Sum Two Numbers"
    assert exercise.entry_function == "add"
    assert exercise.order_index == 1  # editing never moves the exercise
    # PUT is a full replacement, test script, solution and hints included
    assert exercise.test_code == EXERCISE_PAYLOAD["test_code"]
    assert exercise.solution == EXERCISE_PAYLOAD["solution"]
    assert exercise.exercise_hints == EXPECTED_HINTS


def test_delete_exercise_compacts_order(
    client, auth_headers, db_session, tutorial_with_exercises, team
):
    first_id, second_id, third_id = exercise_ids_in_order(
        db_session, tutorial_with_exercises.id
    )
    # Submission history on the deleted exercise must not block deletion.
    db_session.add(
        ExerciseSubmissionMetadata(
            team_id=team.id, exercise_id=second_id, timestamp=utc_now()
        )
    )
    db_session.commit()

    response = client.delete(
        f"/tutorial/exercise/{second_id}", headers=auth_headers
    )
    assert response.status_code == 200

    db_session.expire_all()
    remaining = db_session.exec(
        select(Exercise)
        .where(Exercise.tutorial_id == tutorial_with_exercises.id)
        .order_by(Exercise.order_index)
    ).all()
    assert [e.id for e in remaining] == [first_id, third_id]
    assert [e.order_index for e in remaining] == [0, 1]


def test_reorder_exercises(client, auth_headers, db_session, tutorial_with_exercises):
    ids = exercise_ids_in_order(db_session, tutorial_with_exercises.id)
    new_order = [ids[2], ids[0], ids[1]]
    response = client.post(
        f"/tutorial/tutorial/{tutorial_with_exercises.id}/exercises/reorder",
        json={"exercise_ids": new_order},
        headers=auth_headers,
    )
    assert response.status_code == 200
    detail = response.json()
    assert [e["id"] for e in detail["exercises"]] == new_order

    db_session.expire_all()
    assert exercise_ids_in_order(db_session, tutorial_with_exercises.id) == (
        new_order
    )


def test_reorder_rejects_incomplete_id_list(
    client, auth_headers, db_session, tutorial_with_exercises
):
    ids = exercise_ids_in_order(db_session, tutorial_with_exercises.id)
    response = client.post(
        f"/tutorial/tutorial/{tutorial_with_exercises.id}/exercises/reorder",
        json={"exercise_ids": ids[:2]},
        headers=auth_headers,
    )
    assert response.status_code == 400


# -- dry run ----------------------------------------------------------------


RUN_PAYLOAD = {
    "code": "def add(a, b):\n    return a + b\n",
    "entry_function": "add",
    "test_code": (
        "def test_adds():\n"
        '    """adds two numbers"""\n'
        "    check(add(1, 2), 3)\n"
        "def test_adds_negatives():\n"
        '    """adds negatives"""\n'
        "    check(add(-1, -2), -3)\n"
    ),
}


def test_run_exercise_passes(client, auth_headers, celery_workers):
    response = client.post(
        "/tutorial/admin/run-exercise", json=RUN_PAYLOAD, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["passed"] is True
    assert [t["name"] for t in data["test_results"]] == [
        "adds two numbers",
        "adds negatives",
    ]


def test_run_exercise_failing_test(client, auth_headers, celery_workers):
    payload = {**RUN_PAYLOAD, "code": "def add(a, b):\n    return a - b\n"}
    response = client.post(
        "/tutorial/admin/run-exercise", json=payload, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["passed"] is False


def test_run_exercise_broken_test_script_returns_traceback(
    client, auth_headers, celery_workers
):
    """An admin debugging their own test script gets the traceback — unlike
    the student route, which hides it."""
    payload = {**RUN_PAYLOAD, "test_code": "not_a_defined_helper()\n"}
    response = client.post(
        "/tutorial/admin/run-exercise", json=payload, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "test script failed to run" in data["message"]
    assert "NameError" in data["traceback"]


def test_run_exercise_without_tests_is_an_error(
    client, auth_headers, celery_workers
):
    payload = {**RUN_PAYLOAD, "test_code": None}
    response = client.post(
        "/tutorial/admin/run-exercise", json=payload, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "This exercise defines no tests."


def test_run_exercise_rejects_unsafe_code(client, auth_headers):
    """Unsafe code fails the AST check in the API process — no worker
    needed — so admins see exactly what a student submission would hit."""
    payload = {**RUN_PAYLOAD, "code": "import os\ndef add(a, b):\n    return 0\n"}
    response = client.post(
        "/tutorial/admin/run-exercise", json=payload, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["message"].startswith("Code is not safe")


def test_admin_endpoints_denied_for_team(
    client, team_headers, db_session, tutorial_with_exercises
):
    exercise_id = exercise_ids_in_order(db_session, tutorial_with_exercises.id)[0]
    tutorial_id = tutorial_with_exercises.id
    calls = [
        ("post", "/tutorial/tutorials", {"title": "Nope"}),
        ("put", f"/tutorial/tutorial/{tutorial_id}", {"title": "N", "description": ""}),
        ("delete", f"/tutorial/tutorial/{tutorial_id}", None),
        ("post", f"/tutorial/tutorial/{tutorial_id}/exercises", EXERCISE_PAYLOAD),
        ("put", f"/tutorial/exercise/{exercise_id}", EXERCISE_PAYLOAD),
        ("delete", f"/tutorial/exercise/{exercise_id}", None),
        ("post", "/tutorial/admin/run-exercise", RUN_PAYLOAD),
        (
            "post",
            f"/tutorial/tutorial/{tutorial_id}/exercises/reorder",
            {"exercise_ids": [exercise_id]},
        ),
    ]
    for method, url, payload in calls:
        kwargs = {"headers": team_headers}
        if payload is not None:
            kwargs["json"] = payload
        response = getattr(client, method)(url, **kwargs)
        assert response.status_code == 403, f"{method.upper()} {url}"
