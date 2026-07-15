from datetime import timedelta

import pytest
from sqlmodel import Session, select

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
from backend.time_utils import utc_now

WORD_COUNTER_TEST_CODE = '''\
def test_counts_each_word_once():
    """counts each word once"""
    check(count_words("the cat sat"), {"the": 1, "cat": 1, "sat": 1})


def test_counts_repeated_words():
    """counts repeated words"""
    check(
        count_words("the cat and the dog"),
        {"the": 2, "cat": 1, "and": 1, "dog": 1},
    )


def test_empty_string():
    """empty string has no words"""
    check(count_words(""), {})
'''
WORD_COUNTER_TEST_COUNT = 3

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
    """One tutorial holding two exercises (to check ordering), attached to
    TeamA's league — teams only see tutorials attached to their league."""
    tutorial = Tutorial(
        title="Test Tutorial",
        description="Tutorial used by the router tests",
    )
    db_session.add(tutorial)
    db_session.flush()

    team_a = db_session.exec(select(Team).where(Team.name == "TeamA")).one()
    db_session.add(
        LeagueTutorial(league_id=team_a.league_id, tutorial_id=tutorial.id)
    )

    # Inserted out of order on purpose: order_index must drive the ordering.
    later = Exercise(
        tutorial_id=tutorial.id,
        order_index=1,
        title="Second Exercise",
        problem_markdown="Second problem",
        starter_code="def second():\n    pass\n",
        entry_function="second",
        test_code="def test_returns_none():\n    check(second(), None)\n",
    )
    first = Exercise(
        tutorial_id=tutorial.id,
        order_index=0,
        title="Word Counter",
        problem_markdown="Count the words",
        starter_code="def count_words(sentence):\n    pass\n",
        entry_function="count_words",
        test_code=WORD_COUNTER_TEST_CODE,
        exercise_hints=["Split the sentence.", "Count the pieces."],
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

    # The student sees the problem and hints, not the test definitions
    exercise = data["exercises"][0]
    assert exercise["problem_markdown"] == "Count the words"
    assert exercise["starter_code"].startswith("def count_words")
    assert exercise["exercise_hints"] == [
        "Split the sentence.",
        "Count the pieces.",
    ]
    assert "test_code" not in exercise
    assert "entry_function" not in exercise
    assert "solution" not in exercise

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
    assert len(data["test_results"]) == WORD_COUNTER_TEST_COUNT
    assert all(t["passed"] for t in data["test_results"])

    # The code row is stored and linked to a metadata row, with the per-test
    # rows persisted as returned
    submission = db_session.exec(
        select(ExerciseSubmission).where(
            ExerciseSubmission.id == data["submission_id"]
        )
    ).one()
    assert submission.code == PASSING_CODE
    assert submission.passed is True
    assert submission.test_results == data["test_results"]
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

    # Row names come from the test functions' docstrings
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


PRINT_TEST_CODE = '''\
def test_prints_the_board():
    """prints one line per player, in order"""
    with capture() as out:
        print_scores({"Alice": 30, "Bob": 55})
    check_output(out.text, "Alice: 30\\nBob: 55")


def test_returns_nothing():
    """prints instead of returning"""
    with capture() as out:
        result = print_scores({"Alice": 30})
    check(result, None)
'''


@pytest.fixture
def print_exercise(
    db_session: Session, tutorial_with_exercise: Tutorial
) -> Exercise:
    """A print-checking exercise (capture/check_output) in TeamA's tutorial."""
    exercise = Exercise(
        tutorial_id=tutorial_with_exercise.id,
        order_index=2,
        title="Print Exercise",
        problem_markdown="Print the scoreboard",
        starter_code="def print_scores(banked):\n    pass\n",
        entry_function="print_scores",
        test_code=PRINT_TEST_CODE,
    )
    db_session.add(exercise)
    db_session.commit()
    db_session.refresh(exercise)
    return exercise


def test_submit_print_exercise(
    client, db_session, team_headers, print_exercise, celery_workers
):
    """check_output failures carry raw multiline text, prints outside the
    tests land in the stdout panel, and the rows are stored."""
    response = client.post(
        "/tutorial/submit-exercise",
        json={
            "exercise_id": print_exercise.id,
            "code": (
                "print('debugging outside the tests')\n"
                "def print_scores(banked):\n"
                "    for name in banked:\n"
                "        print(f'{name} has {banked[name]}')\n"
            ),
        },
        headers=team_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is False

    by_name = {t["name"]: t for t in data["test_results"]}
    failed = by_name["prints one line per player, in order"]
    assert failed["passed"] is False
    assert failed["expected"] == "Alice: 30\nBob: 55"
    assert failed["actual"] == "Alice has 30\nBob has 55\n"
    assert by_name["prints instead of returning"]["passed"] is True

    # Module-level prints reach the stdout panel; captured test output doesn't
    assert "debugging outside the tests" in data["stdout"]
    assert "Alice has 30" not in data["stdout"]

    submission = db_session.exec(
        select(ExerciseSubmission).where(
            ExerciseSubmission.id == data["submission_id"]
        )
    ).one()
    assert submission.test_results == data["test_results"]

    # And the fixed version passes
    response = client.post(
        "/tutorial/submit-exercise",
        json={
            "exercise_id": print_exercise.id,
            "code": (
                "def print_scores(banked):\n"
                "    for name in banked:\n"
                "        print(f'{name}: {banked[name]}')\n"
            ),
        },
        headers=team_headers,
    )
    assert response.status_code == 200
    assert response.json()["passed"] is True


def test_submit_exercise_has_no_ast_gate(
    client, db_session, team_headers, word_counter_exercise, celery_workers
):
    """Exercises skip the agent-submission AST safety check entirely: code
    that imports os (forbidden by the agent allowlist) runs on the sandboxed
    exercise worker like any other submission."""
    response = client.post(
        "/tutorial/submit-exercise",
        json={
            "exercise_id": word_counter_exercise.id,
            "code": (
                "import os\n"
                "def count_words(sentence):\n"
                "    assert os.getpid() > 0\n"
                "    counts = {}\n"
                "    for word in sentence.split():\n"
                "        counts[word] = counts.get(word, 0) + 1\n"
                "    return counts\n"
            ),
        },
        headers=team_headers,
    )
    assert response.status_code == 200
    assert response.json()["passed"] is True

    (submission,) = db_session.exec(select(ExerciseSubmission)).all()
    assert submission.passed is True


def test_submit_exercise_error_paths(
    client, team_headers, word_counter_exercise, celery_workers
):
    # Syntax error: no AST pre-check anymore, so it surfaces from the worker
    # when the exec of the student module fails
    response = client.post(
        "/tutorial/submit-exercise",
        json={
            "exercise_id": word_counter_exercise.id,
            "code": "def count_words(sentence)\n    return {}\n",
        },
        headers=team_headers,
    )
    assert response.status_code == 400
    assert "failed to run" in response.json()["detail"]

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
    """An infinite loop is killed by the exercise worker's time limit (0.5s
    soft, 1.5s hard SIGKILL backstop) and reported as a timeout failure."""
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


def test_tutorial_progress(
    client, db_session, team_headers, auth_headers, tutorial_with_exercise
):
    """Progress reports attempted/passed per exercise, in exercise order."""
    exercises = {e.title: e for e in tutorial_with_exercise.exercises}
    word_counter = exercises["Word Counter"]
    second = exercises["Second Exercise"]
    url = f"/tutorial/tutorial/{tutorial_with_exercise.id}/progress"

    # Empty state: every exercise present, nothing attempted
    response = client.get(url, headers=team_headers)
    assert response.status_code == 200
    progress = response.json()["progress"]
    assert [p["exercise_id"] for p in progress] == [word_counter.id, second.id]
    assert all(not p["attempted"] and not p["passed"] for p in progress)

    team = db_session.exec(select(Team).where(Team.name == "TeamA")).one()
    now = utc_now()

    # A failed-to-run attempt on the second exercise: metadata only, no code
    db_session.add(
        ExerciseSubmissionMetadata(
            team_id=team.id, exercise_id=second.id, timestamp=now
        )
    )
    # A failing run then a passing run on the word counter
    for code, passed in [("bad code", False), ("good code", True)]:
        meta = ExerciseSubmissionMetadata(
            team_id=team.id, exercise_id=word_counter.id, timestamp=now
        )
        db_session.add(meta)
        db_session.flush()
        db_session.add(
            ExerciseSubmission(
                code=code,
                timestamp=now,
                passed=passed,
                test_results=[],
                metadata_id=meta.id,
            )
        )
    db_session.commit()

    response = client.get(url, headers=team_headers)
    assert response.status_code == 200
    by_id = {p["exercise_id"]: p for p in response.json()["progress"]}
    assert by_id[word_counter.id]["attempted"] is True
    assert by_id[word_counter.id]["passed"] is True
    assert by_id[second.id]["attempted"] is True
    assert by_id[second.id]["passed"] is False

    # Unknown tutorial 404s; admin tokens are not team tokens
    response = client.get("/tutorial/tutorial/99999/progress", headers=team_headers)
    assert response.status_code == 404
    response = client.get(url, headers=auth_headers)
    assert response.status_code == 403


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


# -- league scoping ---------------------------------------------------------


@pytest.fixture
def unattached_tutorial(db_session: Session) -> Tutorial:
    """A tutorial (with one exercise) not attached to any league."""
    tutorial = Tutorial(
        title="Other League Tutorial",
        description="Not attached to TeamA's league",
    )
    db_session.add(tutorial)
    db_session.flush()
    db_session.add(
        Exercise(
            tutorial_id=tutorial.id,
            order_index=0,
            title="Hidden Exercise",
            problem_markdown="Hidden problem",
            starter_code="def hidden():\n    pass\n",
            entry_function="hidden",
            test_code="def test_runs():\n    check(hidden(), None)\n",
        )
    )
    db_session.commit()
    db_session.refresh(tutorial)
    return tutorial


def test_team_list_scoped_to_league(
    client, team_headers, auth_headers, tutorial_with_exercise, unattached_tutorial
):
    """Teams only see their league's tutorials; admins see the full library."""
    response = client.get("/tutorial/tutorials", headers=team_headers)
    assert response.status_code == 200
    titles = [t["title"] for t in response.json()["tutorials"]]
    assert titles == ["Test Tutorial"]

    response = client.get("/tutorial/tutorials", headers=auth_headers)
    assert response.status_code == 200
    titles = {t["title"] for t in response.json()["tutorials"]}
    assert titles == {"Test Tutorial", "Other League Tutorial"}


def test_team_in_league_without_tutorials_sees_none(
    client, db_session, tutorial_with_exercise
):
    """A team whose league has no attached tutorials gets an empty list and
    404s on tutorials attached to other leagues."""
    from backend.tests.conftest import make_student_token

    league = League(
        name="tutorial_free_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.flush()
    team = Team(
        name="tutorial_free_team",
        school_name="Test School",
        league_id=league.id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    headers = {"Authorization": f"Bearer {make_student_token(team)}"}

    response = client.get("/tutorial/tutorials", headers=headers)
    assert response.status_code == 200
    assert response.json()["tutorials"] == []

    response = client.get(
        f"/tutorial/tutorial/{tutorial_with_exercise.id}", headers=headers
    )
    assert response.status_code == 404


def test_unattached_tutorial_hidden_from_team(
    client, db_session, team_headers, unattached_tutorial
):
    """Detail, progress, submit, and submission-history endpoints all 404
    for a tutorial that isn't attached to the team's league."""
    exercise = db_session.exec(
        select(Exercise).where(Exercise.tutorial_id == unattached_tutorial.id)
    ).one()

    response = client.get(
        f"/tutorial/tutorial/{unattached_tutorial.id}", headers=team_headers
    )
    assert response.status_code == 404

    response = client.get(
        f"/tutorial/tutorial/{unattached_tutorial.id}/progress",
        headers=team_headers,
    )
    assert response.status_code == 404

    response = client.post(
        "/tutorial/submit-exercise",
        json={"exercise_id": exercise.id, "code": PASSING_CODE},
        headers=team_headers,
    )
    assert response.status_code == 404
    # The blocked attempt is not recorded
    assert db_session.exec(select(ExerciseSubmissionMetadata)).all() == []

    response = client.get(
        f"/tutorial/exercise/{exercise.id}/latest-submission",
        headers=team_headers,
    )
    assert response.status_code == 404

    response = client.get(
        f"/tutorial/exercise/{exercise.id}/submissions", headers=team_headers
    )
    assert response.status_code == 404


def test_admin_can_open_unattached_tutorial(
    client, auth_headers, unattached_tutorial
):
    response = client.get(
        f"/tutorial/tutorial/{unattached_tutorial.id}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Other League Tutorial"
