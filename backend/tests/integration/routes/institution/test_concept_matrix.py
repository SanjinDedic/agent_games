"""GET /institution/classroom/{league_id}/concept-matrix: student x concept
mastery grid, rolled up from exercise attempts through the concept tags.

The scoring rules themselves are pinned in
backend/tests/unit/routes/institution/test_concept_mastery.py; this covers the
rollup, the payload shape and the access rules.
"""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlmodel import Session

from backend.database.db_models import (
    Concept,
    Exercise,
    ExerciseConcept,
    ExerciseHintReveal,
    Lesson,
    LessonConcept,
)
from backend.time_utils import utc_now


@pytest.fixture
def concept_setup(db_session: Session, classroom_setup) -> SimpleNamespace:
    """Concept tags on top of the shared classroom fixture.

    loops   -> exercise one + exercise two   (has a lesson)
    dicts   -> exercise one                  (no lesson)
    offside -> the other tutorial's exercise, which is NOT attached to 9a
    exercise three is deliberately left untagged.

    The attempts come from classroom_setup: adam failed then passed exercise
    one (2 attempts, no hints); zoe's single attempt never ran.
    """
    s = classroom_setup
    exercise_one, exercise_two, exercise_other = s.exercises

    exercise_three = Exercise(
        tutorial_id=s.tutorial_one.id,
        order_index=2,
        title="Exercise Three",
        problem_markdown="p",
        entry_function="solve",
    )
    db_session.add(exercise_three)

    loops = Concept(
        slug="loops", name="Loops", description="Repeating work.",
        category="control-flow",
    )
    dicts = Concept(
        slug="dicts", name="Dictionaries", description="Key-value pairs.",
        category="data-structures",
    )
    offside = Concept(
        slug="offside", name="Offside", description="Other tutorial only.",
        category="basics",
    )
    for concept in (loops, dicts, offside):
        db_session.add(concept)
    db_session.commit()

    lesson = Lesson(slug="loops-lesson", title="Loops", content="body")
    db_session.add(lesson)
    db_session.commit()
    db_session.add(LessonConcept(lesson_id=lesson.id, concept_id=loops.id))

    for exercise_id, concept_id in (
        (exercise_one.id, loops.id),
        (exercise_two.id, loops.id),
        (exercise_one.id, dicts.id),
        (exercise_other.id, offside.id),
    ):
        db_session.add(
            ExerciseConcept(exercise_id=exercise_id, concept_id=concept_id)
        )
    db_session.commit()

    return SimpleNamespace(
        **vars(s),
        loops=loops,
        dicts=dicts,
        offside=offside,
        exercise_three=exercise_three,
    )


def _by_id(rows, key="id"):
    return {row[key]: row for row in rows}


def _matrix(client, setup):
    response = client.get(
        f"/institution/classroom/{setup.league_a.id}/concept-matrix",
        headers=setup.owner_headers,
    )
    assert response.status_code == 200
    return response.json()


def _cells(data):
    return {(c["team_id"], c["concept_id"]): c for c in data["cells"]}


def _grind_to_a_pass(db_session, team_id, exercise_id, failures, start):
    """`failures` failed attempts then a pass, on rising timestamps."""
    from backend.tests.conftest import add_exercise_attempt

    for offset in range(failures):
        add_exercise_attempt(
            db_session,
            team_id,
            exercise_id,
            passed=False,
            timestamp=start + timedelta(seconds=offset),
        )
    add_exercise_attempt(
        db_session,
        team_id,
        exercise_id,
        passed=True,
        timestamp=start + timedelta(seconds=failures),
    )


def test_concept_matrix_success(client, concept_setup):
    s = concept_setup
    data = _matrix(client, s)

    assert data["league"] == {"id": s.league_a.id, "name": "classroom_9a"}
    assert [team["name"] for team in data["teams"]] == ["adam", "zoe"]

    # Only concepts tagged on exercises of the classroom's tutorials, sorted
    # by category then curriculum order: control-flow before data-structures.
    assert [c["slug"] for c in data["concepts"]] == ["loops", "dicts"]

    concepts = _by_id(data["concepts"])
    loops = concepts[s.loops.id]
    assert loops["name"] == "Loops"
    assert loops["category"] == "control-flow"
    assert loops["order_index"] == 0
    assert [e["title"] for e in loops["exercises"]] == [
        "Exercise One",
        "Exercise Two",
    ]
    # The lesson to send a struggling class to.
    assert loops["lesson_slug"] == "loops-lesson"
    assert concepts[s.dicts.id]["lesson_slug"] is None

    # Exercise three carries no tags, and the payload says so.
    assert data["exercises_total"] == 3
    assert data["untagged_exercises"] == 1


def test_mastery_reflects_attempts_to_pass(client, concept_setup):
    s = concept_setup
    data = _matrix(client, s)
    cells = _cells(data)

    # adam passed exercise one on his second go with no hints: effort 2 -> 85.
    adam = cells[(s.adam.id, s.loops.id)]
    assert adam["mastery"] == 85
    assert adam["band"] == 1
    assert adam["band_key"] == "approaching_mastery"
    assert adam["exercises_passed"] == 1
    assert adam["exercises_touched"] == 1
    assert adam["exercises_total"] == 2
    assert adam["attempts"] == 2
    assert adam["avg_attempts_to_pass"] == 2.0
    assert adam["hints_used"] == 0
    assert adam["last_attempt_at"] is not None

    # zoe's only attempt never ran, so she has not passed: bottom band.
    zoe = cells[(s.zoe.id, s.loops.id)]
    assert zoe["mastery"] == 0
    assert zoe["band"] == 4
    assert zoe["band_key"] == "needs_help"
    assert zoe["exercises_passed"] == 0
    assert zoe["attempts"] == 1
    assert zoe["avg_attempts_to_pass"] is None

    # Class figures average the students who reached it.
    loops = _by_id(data["concepts"])[s.loops.id]
    assert loops["class_mastery"] == 42
    assert loops["band"] == 3
    assert loops["reached"] == 2
    assert loops["needs_attention"] == 1


def test_first_go_pass_is_the_top_band(client, db_session, concept_setup):
    """A clean first-attempt pass is the top of the scale."""
    from backend.tests.conftest import add_exercise_attempt

    s = concept_setup
    _, exercise_two, _ = s.exercises
    add_exercise_attempt(db_session, s.zoe.id, exercise_two.id, passed=True)
    db_session.commit()

    zoe = _cells(_matrix(client, s))[(s.zoe.id, s.loops.id)]
    # One exercise failed (0) and one passed first go (100) -> 50, band 3.
    assert zoe["exercises_touched"] == 2
    assert zoe["mastery"] == 50
    assert zoe["band"] == 3
    assert zoe["band_key"] == "progressing_slowly"


def test_revealed_hints_cost_less_than_an_attempt(
    client, db_session, concept_setup
):
    """A hint is a nudge, not a failed attempt — it costs half a go."""
    s = concept_setup
    exercise_one, _, _ = s.exercises
    db_session.add(
        ExerciseHintReveal(
            team_id=s.adam.id, exercise_id=exercise_one.id, hint_index=0
        )
    )
    db_session.commit()

    adam = _cells(_matrix(client, s))[(s.adam.id, s.loops.id)]
    # 2 attempts + half a go = effort 2.5, one band below the 85 without it.
    assert adam["hints_used"] == 1
    assert adam["mastery"] == 70
    assert adam["band"] == 2


def test_hint_cost_is_capped(client, db_session, concept_setup):
    """A student who reads every hint loses one band step, not six. Without
    the cap this would fall two buckets further."""
    s = concept_setup
    exercise_one, _, _ = s.exercises
    for hint_index in range(6):
        db_session.add(
            ExerciseHintReveal(
                team_id=s.adam.id,
                exercise_id=exercise_one.id,
                hint_index=hint_index,
            )
        )
    db_session.commit()

    adam = _cells(_matrix(client, s))[(s.adam.id, s.loops.id)]
    assert adam["hints_used"] == 6
    # Identical to the single-hint case above.
    assert adam["mastery"] == 70
    assert adam["band"] == 2


def test_passing_everything_cannot_fall_below_band_two(
    client, db_session, concept_setup
):
    """The completion floor: finishing every exercise for a concept counts,
    however many goes and hints it took."""
    s = concept_setup
    exercise_one, exercise_two, _ = s.exercises
    start = utc_now()
    _grind_to_a_pass(db_session, s.zoe.id, exercise_one.id, 9, start)
    _grind_to_a_pass(
        db_session, s.zoe.id, exercise_two.id, 9, start + timedelta(minutes=1)
    )
    for hint_index in range(3):
        db_session.add(
            ExerciseHintReveal(
                team_id=s.zoe.id,
                exercise_id=exercise_one.id,
                hint_index=hint_index,
            )
        )
    db_session.commit()

    zoe = _cells(_matrix(client, s))[(s.zoe.id, s.loops.id)]
    assert zoe["exercises_passed"] == zoe["exercises_total"] == 2
    assert zoe["hints_used"] == 3
    # Both exercises scored the floor of the effort scale on their own.
    assert zoe["mastery"] == 60
    assert zoe["band"] == 2
    # ...and she is therefore off the list of students needing help.
    assert not [
        item
        for item in _matrix(client, s)["attention"]
        if item["team_id"] == s.zoe.id and item["concept_id"] == s.loops.id
    ]


def test_confidence_grows_with_the_number_of_exercises(
    client, db_session, concept_setup
):
    """One exercise is an anecdote. The payload says how far to trust a cell
    so the UI can hedge its wording."""
    from backend.tests.conftest import add_exercise_attempt

    s = concept_setup
    exercise_one, exercise_two, _ = s.exercises
    repeated = Concept(
        slug="repeated", name="Repeated", description="Taught thrice.",
        category="basics",
    )
    db_session.add(repeated)
    db_session.commit()
    for exercise_id in (exercise_one.id, exercise_two.id, s.exercise_three.id):
        db_session.add(
            ExerciseConcept(exercise_id=exercise_id, concept_id=repeated.id)
        )
    db_session.commit()

    # adam has touched one of the three so far.
    data = _matrix(client, s)
    assert _cells(data)[(s.adam.id, repeated.id)]["confidence"] == "low"
    # Three exercises is enough for the reading to be stated plainly.
    assert _by_id(data["concepts"])[repeated.id]["under_assessed"] is False

    add_exercise_attempt(db_session, s.adam.id, exercise_two.id, passed=True)
    db_session.commit()
    assert (
        _cells(_matrix(client, s))[(s.adam.id, repeated.id)]["confidence"]
        == "medium"
    )

    add_exercise_attempt(
        db_session, s.adam.id, s.exercise_three.id, passed=True
    )
    db_session.commit()
    assert (
        _cells(_matrix(client, s))[(s.adam.id, repeated.id)]["confidence"]
        == "high"
    )


def test_thinly_taught_concepts_are_flagged(client, concept_setup):
    """A concept practised once or twice is reported as such, so a weak
    reading is never mistaken for a confident one."""
    s = concept_setup
    data = _matrix(client, s)
    concepts = _by_id(data["concepts"])

    assert concepts[s.loops.id]["exercises_total"] == 2
    assert concepts[s.loops.id]["under_assessed"] is True
    assert concepts[s.dicts.id]["exercises_total"] == 1
    assert concepts[s.dicts.id]["under_assessed"] is True
    assert data["under_assessed_concepts"] == 2


def test_attention_lists_who_to_help_worst_first(
    client, db_session, concept_setup
):
    """The headline of the whole tab: which student, which concept."""
    from backend.tests.conftest import add_exercise_attempt

    s = concept_setup
    _, exercise_two, _ = s.exercises
    # Lift zoe's loops cell out of the bottom band and into band 3, so the
    # ordering between bands is actually exercised.
    add_exercise_attempt(db_session, s.zoe.id, exercise_two.id, passed=True)
    db_session.commit()

    data = _matrix(client, s)
    attention = data["attention"]

    # adam is in the top band everywhere and must not appear.
    assert {item["team_id"] for item in attention} == {s.zoe.id}
    # Worst band first: dicts (nothing passed) before loops (half passed).
    assert [item["concept_id"] for item in attention] == [
        s.dicts.id,
        s.loops.id,
    ]
    assert [item["band"] for item in attention] == [4, 3]
    assert all(item["confidence"] in ("low", "medium") for item in attention)


def test_scoring_model_ships_with_the_payload(client, concept_setup):
    """Teachers get the rules, generated from the code that applies them."""
    from backend.routes.institution.concept_mastery import (
        COMPLETION_FLOOR,
        MIN_ASSESSMENTS,
        describe_mastery_model,
    )

    data = _matrix(client, concept_setup)
    assert data["scoring"] == describe_mastery_model()
    assert data["scoring"]["completion_floor"] == COMPLETION_FLOOR
    assert data["scoring"]["min_assessments"] == MIN_ASSESSMENTS
    assert [band["band"] for band in data["scoring"]["bands"]] == [1, 2, 3, 4]


def test_unreached_concepts_are_omitted(client, db_session, concept_setup):
    """A concept nobody has attempted is absent, not a zero — a student who
    has not got there yet is not struggling."""
    s = concept_setup
    lists = Concept(
        slug="lists", name="Lists", description="Ordered.", category="basics"
    )
    db_session.add(lists)
    db_session.commit()
    db_session.add(
        ExerciseConcept(
            exercise_id=s.exercise_three.id, concept_id=lists.id
        )
    )
    db_session.commit()

    data = _matrix(client, s)
    listed = _by_id(data["concepts"])[lists.id]
    assert listed["class_mastery"] is None
    assert listed["band"] is None
    assert listed["reached"] == 0
    assert not [c for c in data["cells"] if c["concept_id"] == lists.id]
    # Now that exercise three is tagged, nothing is untagged.
    assert data["untagged_exercises"] == 0


def test_matrix_without_concepts(client, classroom_setup):
    """An untagged classroom returns an empty map rather than failing."""
    s = classroom_setup
    response = client.get(
        f"/institution/classroom/{s.rival_league.id}/concept-matrix",
        headers=s.rival_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["concepts"] == []
    assert data["cells"] == []
    assert data["attention"] == []
    assert data["under_assessed_concepts"] == 0
    assert [team["name"] for team in data["teams"]] == ["rival_student"]


def test_matrix_access_control(client, team_headers, concept_setup):
    s = concept_setup
    url = f"/institution/classroom/{s.league_a.id}/concept-matrix"

    assert client.get(url).status_code == 401
    assert client.get(url, headers=s.rival_headers).status_code == 403
    assert client.get(url, headers=team_headers).status_code == 403
    assert (
        client.get(
            "/institution/classroom/999999/concept-matrix",
            headers=s.owner_headers,
        ).status_code
        == 404
    )


def test_matrix_admin_bypass(client, auth_headers, concept_setup):
    s = concept_setup
    response = client.get(
        f"/institution/classroom/{s.league_a.id}/concept-matrix",
        headers=auth_headers,
    )
    assert response.status_code == 200
