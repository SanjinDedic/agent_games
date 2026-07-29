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
        slug="loops", name="Loops", shortname="For Loops",
        description="Repeating work.", category="control-flow",
    )
    # No shortname: authored before they existed, so the payload carries null
    # and the client falls back to the full name.
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


def _grind_to_a_pass(
    db_session, team_id, exercise_id, failures, start, minutes=0
):
    """`failures` failed attempts then a pass `minutes` after the first go."""
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
        timestamp=start + timedelta(minutes=minutes, seconds=failures),
    )


def _reveal_hints(db_session, team_id, exercise_id, count):
    for hint_index in range(count):
        db_session.add(
            ExerciseHintReveal(
                team_id=team_id,
                exercise_id=exercise_id,
                hint_index=hint_index,
            )
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
    # The column heading, and null when the concept has none of its own.
    assert loops["shortname"] == "For Loops"
    assert concepts[s.dicts.id]["shortname"] is None
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


def test_cells_carry_exposure_and_fluency(client, concept_setup):
    """The two numbers the whole tab is built on: how much of the concept's
    work is finished, and how the finished work went."""
    s = concept_setup
    data = _matrix(client, s)
    cells = _cells(data)

    # adam passed exercise one a minute after his first go — full marks — and
    # that is one of the two exercises loops is taught on.
    adam = cells[(s.adam.id, s.loops.id)]
    assert adam["fluency"] == 100
    assert adam["band"] == 1
    assert adam["band_key"] == "fluent"
    assert adam["exposure"] == 50
    assert adam["exposure_band"] == 2
    assert adam["exposure_band_key"] == "part_way"
    assert adam["exercises_attempted"] == 1
    assert adam["exercises_passed"] == 1
    assert adam["exercises_total"] == 2
    assert adam["attempts"] == 2
    assert adam["avg_attempts_to_pass"] == 2.0
    assert adam["avg_minutes_to_pass"] == 1
    assert adam["hints_used"] == 0
    assert adam["needs_help"] is False
    assert adam["last_attempt_at"] is not None

    # zoe has had exactly one go, which never ran. She gets a cell — she has
    # been here — but one go is not something to judge, so there is no fluency
    # at all rather than a zero.
    zoe = cells[(s.zoe.id, s.loops.id)]
    assert zoe["fluency"] is None
    assert zoe["band"] is None
    assert zoe["exposure"] == 0
    assert zoe["exercises_attempted"] == 1
    assert zoe["exercises_passed"] == 0
    assert zoe["avg_attempts_to_pass"] is None
    assert zoe["needs_help"] is False

    # The class is one average student, and nobody is flagged: half the class
    # has finished half of it, and what they finished went well.
    loops = _by_id(data["concepts"])[s.loops.id]
    assert loops["class_exposure"] == 25
    assert loops["class_fluency"] == 100
    assert loops["reached"] == 2
    assert loops["needs_attention"] == 0
    assert loops["reteach"] is False


def test_work_in_progress_moves_exposure_but_never_fluency(
    client, db_session, concept_setup
):
    """The change that stops the page crying wolf. zoe has one exercise still
    in its opening goes and one passed cleanly: the unfinished one is missing
    coverage, not evidence of a struggle."""
    from backend.tests.conftest import add_exercise_attempt

    s = concept_setup
    _, exercise_two, _ = s.exercises
    add_exercise_attempt(db_session, s.zoe.id, exercise_two.id, passed=True)
    db_session.commit()

    zoe = _cells(_matrix(client, s))[(s.zoe.id, s.loops.id)]
    assert zoe["exercises_attempted"] == 2
    assert zoe["exercises_passed"] == 1
    assert zoe["exposure"] == 50
    assert zoe["fluency"] == 100
    assert zoe["band"] == 1


def test_a_real_struggle_counts_as_a_zero(client, db_session, concept_setup):
    """Past the opening goes, an unfinished exercise is the only thing that can
    pull fluency below what finishing is worth."""
    from backend.tests.conftest import add_exercise_attempt

    s = concept_setup
    exercise_one, exercise_two, _ = s.exercises
    start = utc_now() - timedelta(hours=1)
    for offset in range(4):
        add_exercise_attempt(
            db_session,
            s.zoe.id,
            exercise_one.id,
            passed=False,
            timestamp=start + timedelta(seconds=offset),
        )
    add_exercise_attempt(db_session, s.zoe.id, exercise_two.id, passed=True)
    db_session.commit()

    zoe = _cells(_matrix(client, s))[(s.zoe.id, s.loops.id)]
    assert zoe["exercises_passed"] == 1
    # A clean pass (100) and a genuine non-pass (0).
    assert zoe["fluency"] == 50
    assert zoe["band"] == 3
    assert zoe["band_key"] == "progressing_slowly"


def test_a_fast_pass_is_full_marks_however_it_was_reached(
    client, db_session, concept_setup
):
    """Charging a student for the hints they read on the way to a two-minute
    pass only teaches them to avoid the hints."""
    s = concept_setup
    exercise_one, _, _ = s.exercises
    _reveal_hints(db_session, s.adam.id, exercise_one.id, 6)
    db_session.commit()

    adam = _cells(_matrix(client, s))[(s.adam.id, s.loops.id)]
    assert adam["hints_used"] == 6
    assert adam["fluency"] == 100


def test_a_slow_pass_pays_for_hints_and_a_long_run_of_goes(
    client, db_session, concept_setup
):
    s = concept_setup
    _, exercise_two, _ = s.exercises
    start = utc_now() - timedelta(hours=1)
    # Eight failed goes and a pass twelve minutes in: two blocks past the free
    # window (-10), two hints (-10), more than five goes (-10).
    _grind_to_a_pass(db_session, s.zoe.id, exercise_two.id, 8, start, minutes=12)
    _reveal_hints(db_session, s.zoe.id, exercise_two.id, 2)
    db_session.commit()

    zoe = _cells(_matrix(client, s))[(s.zoe.id, s.loops.id)]
    assert zoe["fluency"] == 70
    assert zoe["avg_minutes_to_pass"] == 12


def test_hint_cost_is_capped(client, db_session, concept_setup):
    """A student who opens every hint and finishes must never read like one who
    never finished at all."""
    s = concept_setup
    _, exercise_two, _ = s.exercises
    start = utc_now() - timedelta(hours=1)
    _grind_to_a_pass(db_session, s.zoe.id, exercise_two.id, 8, start, minutes=12)
    _reveal_hints(db_session, s.zoe.id, exercise_two.id, 9)
    db_session.commit()

    zoe = _cells(_matrix(client, s))[(s.zoe.id, s.loops.id)]
    assert zoe["hints_used"] == 9
    # Nine hints cost the same as three: -10 time, -15 hints, -10 goes.
    assert zoe["fluency"] == 65


def test_finishing_everything_is_never_an_alert(
    client, db_session, concept_setup
):
    """The floor, end to end: the worst run of a concept a student can finish
    still lands on the line, so it takes unfinished work to fall below it."""
    from backend.routes.institution.concept_mastery import COMPLETED_FLOOR

    s = concept_setup
    exercise_one, exercise_two, _ = s.exercises
    start = utc_now() - timedelta(hours=3)
    for index, exercise in enumerate((exercise_one, exercise_two)):
        _grind_to_a_pass(
            db_session,
            s.zoe.id,
            exercise.id,
            9,
            start + timedelta(hours=index),
            minutes=45,
        )
        _reveal_hints(db_session, s.zoe.id, exercise.id, 3)
    db_session.commit()

    data = _matrix(client, s)
    zoe = _cells(data)[(s.zoe.id, s.loops.id)]
    assert zoe["exercises_passed"] == zoe["exercises_total"] == 2
    assert zoe["exposure"] == 100
    assert zoe["fluency"] == COMPLETED_FLOOR
    assert zoe["band"] == 2
    assert zoe["needs_help"] is False
    assert not [
        item
        for item in data["attention"]
        if item["team_id"] == s.zoe.id and item["concept_id"] == s.loops.id
    ]


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


@pytest.fixture
def wide_concept(db_session: Session, concept_setup) -> SimpleNamespace:
    """A concept taught on five exercises, so exposure has room to move.

    Both students finish four of the five and never finish the fifth; adam's
    four cost him everything an exercise can cost, zoe's cost slightly less.
    """
    s = concept_setup
    from backend.tests.conftest import add_exercise_attempt

    exercises = []
    for index in range(5):
        exercise = Exercise(
            tutorial_id=s.tutorial_one.id,
            order_index=3 + index,
            title=f"Wide {index}",
            problem_markdown="p",
            entry_function="solve",
        )
        db_session.add(exercise)
        exercises.append(exercise)
    wide = Concept(
        slug="wide", name="Wide", description="Taught five times.",
        category="basics",
    )
    db_session.add(wide)
    db_session.commit()
    for exercise in exercises:
        db_session.add(
            ExerciseConcept(exercise_id=exercise.id, concept_id=wide.id)
        )

    start = utc_now() - timedelta(days=1)
    for index, exercise in enumerate(exercises[:4]):
        # adam: 45 minutes, 3 hints, a long run of goes — the cheapest a
        # finished exercise can be. zoe: the same but faster.
        _grind_to_a_pass(
            db_session, s.adam.id, exercise.id, 8,
            start + timedelta(hours=index), minutes=45,
        )
        _reveal_hints(db_session, s.adam.id, exercise.id, 3)
        _grind_to_a_pass(
            db_session, s.zoe.id, exercise.id, 8,
            start + timedelta(hours=index), minutes=12,
        )
        _reveal_hints(db_session, s.zoe.id, exercise.id, 3)
    # ...and neither of them gets through the fifth.
    for team_id in (s.adam.id, s.zoe.id):
        for offset in range(4):
            add_exercise_attempt(
                db_session, team_id, exercises[4].id, passed=False,
                timestamp=start + timedelta(days=1, seconds=offset),
            )
    db_session.commit()

    return SimpleNamespace(**vars(s), wide=wide, wide_exercises=exercises)


def test_attention_lists_who_to_help_worst_first(client, wide_concept):
    """The headline of the whole tab: which student, which concept."""
    s = wide_concept
    data = _matrix(client, s)
    attention = data["attention"]

    # Only the concept both students have covered and still gone badly on.
    assert {item["concept_id"] for item in attention} == {s.wide.id}
    # Worst fluency first: adam's four passes cost more than zoe's.
    assert [item["team_id"] for item in attention] == [s.adam.id, s.zoe.id]
    assert all(item["band"] in (3, 4) for item in attention)

    cells = _cells(data)
    adam = cells[(s.adam.id, s.wide.id)]
    assert adam["exercises_attempted"] == 5
    assert adam["exercises_passed"] == 4
    assert adam["exposure"] == 80  # four of five finished
    assert adam["fluency"] == 48  # (60, 60, 60, 60, 0)
    assert adam["needs_help"] is True
    assert cells[(s.zoe.id, s.wide.id)]["fluency"] == 52  # (65 x4, 0)


def test_reteach_wants_a_class_that_covered_it_and_still_struggled(
    client, wide_concept
):
    """Both halves of the rule, at class level — the same test a single student
    gets, applied to the average one."""
    s = wide_concept
    concepts = _by_id(_matrix(client, s)["concepts"])

    wide = concepts[s.wide.id]
    assert wide["class_exposure"] == 80
    assert wide["class_fluency"] == 50
    assert wide["needs_attention"] == 2
    assert wide["reteach"] is True

    # loops went fine for everyone who got to it, and half the class has not
    # been near it — neither is a reason to stand at the whiteboard.
    assert concepts[s.loops.id]["reteach"] is False


def test_scoring_model_ships_with_the_payload(client, concept_setup):
    """Teachers get the rules, generated from the code that applies them."""
    from backend.routes.institution.concept_mastery import (
        COMPLETED_FLOOR,
        MIN_ASSESSMENTS,
        describe_mastery_model,
    )

    data = _matrix(client, concept_setup)
    assert data["scoring"] == describe_mastery_model()
    assert data["scoring"]["completed_floor"] == COMPLETED_FLOOR
    assert data["scoring"]["min_assessments"] == MIN_ASSESSMENTS
    assert [band["band"] for band in data["scoring"]["bands"]] == [1, 2, 3, 4]
    assert [
        band["band"] for band in data["scoring"]["exposure_bands"]
    ] == [1, 2, 3, 4]


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
    assert listed["class_exposure"] is None
    assert listed["class_fluency"] is None
    assert listed["band"] is None
    assert listed["exposure_band"] is None
    assert listed["reteach"] is False
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
