from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    Exercise,
    ExerciseHintReveal,
    ExerciseSubmission,
    ExerciseSubmissionMetadata,
    League,
    LeagueTutorial,
    Team,
    Tutorial,
)
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

    # The test script and entry function ship to the browser (Pyodide runs
    # exercises locally); only the reference solution stays server-side
    exercise = data["exercises"][0]
    assert exercise["problem_markdown"] == "Count the words"
    assert exercise["starter_code"].startswith("def count_words")
    assert exercise["exercise_hints"] == [
        "Split the sentence.",
        "Count the pieces.",
    ]
    assert exercise["entry_function"] == "count_words"
    assert exercise["test_code"] == WORD_COUNTER_TEST_CODE
    assert "solution" not in exercise

    response = client.get("/tutorial/tutorial/99999", headers=team_headers)
    assert response.status_code == 404


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
    """Detail, progress, and submission-history endpoints all 404 for a
    tutorial that isn't attached to the team's league."""
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


# -- hint reveals -----------------------------------------------------------


def test_record_hint_reveal(
    client, db_session, team_headers, word_counter_exercise
):
    """A revealed hint is recorded so concept mastery can count it as effort."""
    response = client.post(
        f"/tutorial/exercise/{word_counter_exercise.id}/hint-revealed",
        json={"hint_index": 0},
        headers=team_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

    reveals = db_session.exec(select(ExerciseHintReveal)).all()
    assert len(reveals) == 1
    assert reveals[0].exercise_id == word_counter_exercise.id
    assert reveals[0].hint_index == 0
    assert reveals[0].revealed_at is not None


def test_record_hint_reveal_is_idempotent(
    client, db_session, team_headers, word_counter_exercise
):
    """The client fires on every reveal, including after a reload — a repeat
    must not inflate the count."""
    url = f"/tutorial/exercise/{word_counter_exercise.id}/hint-revealed"
    for _ in range(3):
        assert client.post(
            url, json={"hint_index": 0}, headers=team_headers
        ).status_code == 200
    assert client.post(
        url, json={"hint_index": 1}, headers=team_headers
    ).status_code == 200

    reveals = db_session.exec(select(ExerciseHintReveal)).all()
    assert sorted(reveal.hint_index for reveal in reveals) == [0, 1]


def test_record_hint_reveal_rejects_negative_index(
    client, team_headers, word_counter_exercise
):
    response = client.post(
        f"/tutorial/exercise/{word_counter_exercise.id}/hint-revealed",
        json={"hint_index": -1},
        headers=team_headers,
    )
    assert response.status_code == 422


def test_record_hint_reveal_outside_league_404s(
    client, db_session, team_headers, unattached_tutorial
):
    """Same league gate as every other exercise endpoint."""
    exercise = db_session.exec(
        select(Exercise).where(Exercise.tutorial_id == unattached_tutorial.id)
    ).first()
    response = client.post(
        f"/tutorial/exercise/{exercise.id}/hint-revealed",
        json={"hint_index": 0},
        headers=team_headers,
    )
    assert response.status_code == 404
    assert db_session.exec(select(ExerciseHintReveal)).all() == []
