"""The concept mastery scoring model, pinned without a database.

The endpoint test covers the rollup; this covers the arithmetic itself, so a
threshold cannot be changed without a test saying what it means.
"""

import pytest

from backend.routes.institution.concept_mastery import (
    ATTEMPTS_BEFORE_COUNTED,
    COMPLETED_FLOOR,
    EXPOSURE_BANDS,
    FLUENCY_BANDS,
    FULL_MARKS,
    MANY_ATTEMPTS,
    MAX_HINT_PENALTY,
    MIN_ASSESSMENTS,
    NOT_PASSED_POINTS,
    describe_mastery_model,
    exercise_points,
    exercise_score,
    exposure_band,
    exposure_for,
    fluency_band,
    fluency_for,
    needs_help,
    time_penalty,
)


@pytest.mark.parametrize(
    "minutes,expected",
    [
        (0, 0),      # passed on the first submission
        (5, 0),      # exactly on the free window's edge, still free
        (5.5, 5),
        (10, 5),
        (12, 10),
        (20, 15),
        (25, 20),
        (90, 20),    # the cap: an hour and a day read the same
    ],
)
def test_time_penalty(minutes, expected):
    assert time_penalty(minutes) == expected


def test_missing_time_is_treated_as_fast():
    """Data from before the clock was recorded must not invent a slow student."""
    assert time_penalty(None) == 0


@pytest.mark.parametrize(
    "minutes,hints,attempts,expected",
    [
        (3, 0, 1, 100),   # quick and clean
        (3, 4, 9, 100),   # quick, whatever it took to get there
        (8, 0, 1, 95),    # one block over
        (8, 2, 1, 85),    # ...and two hints
        (8, 2, 9, 75),    # ...and a long run of goes
        (25, 3, 9, COMPLETED_FLOOR),
        (60, 9, 40, COMPLETED_FLOOR),  # every penalty maxed is still the floor
    ],
)
def test_exercise_score(minutes, hints, attempts, expected):
    assert exercise_score(minutes, hints, attempts) == expected


def test_a_fast_pass_ignores_hints_and_goes():
    """Speed is the headline signal. Charging a student for the hints they read
    on the way to a five-minute pass only teaches them to avoid the hints."""
    assert exercise_score(1, 9, 20) == FULL_MARKS


def test_hint_and_attempt_penalties_are_capped():
    many_hints = exercise_score(8, 99, 1)
    three_hints = exercise_score(8, MAX_HINT_PENALTY // 5, 1)
    assert many_hints == three_hints

    # The attempt charge is flat, not a slope: six goes and sixty are the same
    # message to a teacher.
    assert exercise_score(8, 0, MANY_ATTEMPTS + 1) == exercise_score(8, 0, 600)
    assert exercise_score(8, 0, MANY_ATTEMPTS) > exercise_score(
        8, 0, MANY_ATTEMPTS + 1
    )


def test_completing_an_exercise_can_never_score_below_the_floor():
    """Finishing is worth a lot, and the floor is what says so."""
    assert COMPLETED_FLOOR == 55  # 100 - 20 time - 15 hints - 10 goes
    assert exercise_score(10_000, 99, 99) == COMPLETED_FLOOR


def test_an_unpassed_exercise_scores_nothing_once_really_attempted():
    assert (
        exercise_points(False, ATTEMPTS_BEFORE_COUNTED + 1, 0, None)
        == NOT_PASSED_POINTS
    )


def test_an_unpassed_exercise_in_its_first_goes_is_not_judged():
    """A student part-way through their second try is not a student in trouble,
    and counting them as a zero is how the page cries wolf."""
    for attempts in range(1, ATTEMPTS_BEFORE_COUNTED + 1):
        assert exercise_points(False, attempts, 0, None) is None


def test_fluency_leaves_out_what_cannot_be_judged():
    assert fluency_for([100, None, 80]) == 90
    assert fluency_for([None, None]) is None
    assert fluency_for([]) is None


def test_fluency_counts_a_real_failure_as_a_zero():
    """The one thing that can pull fluency under the completed-exercise floor,
    and so the only thing that can put a concept on the reteach list."""
    passed = exercise_points(True, 1, 0, 1)
    failed = exercise_points(False, ATTEMPTS_BEFORE_COUNTED + 1, 0, None)
    assert fluency_for([passed, failed]) == 50


def test_exposure_is_finished_work_over_all_of_it():
    assert exposure_for(0, 4) == 0
    assert exposure_for(3, 4) == 75
    assert exposure_for(4, 4) == 100
    assert exposure_for(0, 0) == 0


def test_bands_cover_every_value():
    assert [band["band"] for band in FLUENCY_BANDS] == [1, 2, 3, 4]
    assert fluency_band(100)["key"] == "approaching_mastery"
    assert fluency_band(85)["key"] == "approaching_mastery"
    assert fluency_band(84)["key"] == "showing_understanding"
    assert fluency_band(55)["key"] == "showing_understanding"
    assert fluency_band(54)["key"] == "progressing_slowly"
    assert fluency_band(27)["key"] == "progressing_slowly"
    assert fluency_band(26)["key"] == "needs_help"
    assert fluency_band(0)["key"] == "needs_help"
    assert fluency_band(None) is None

    assert [band["band"] for band in EXPOSURE_BANDS] == [1, 2, 3, 4]
    assert exposure_band(100)["key"] == "most_or_all"
    assert exposure_band(80)["key"] == "most_or_all"
    assert exposure_band(79)["key"] == "part_way"
    assert exposure_band(1)["key"] == "just_begun"
    assert exposure_band(0)["key"] == "none_yet"


def test_the_attention_line_sits_exactly_on_the_completed_floor():
    """The rule that keeps the page honest: a student whose every completed
    exercise cost as much as an exercise can cost still sits on the line, so
    anything below it means work that was never finished at all."""
    assert fluency_band(COMPLETED_FLOOR)["band"] not in (3, 4)
    assert fluency_band(COMPLETED_FLOOR - 1)["band"] in (3, 4)


def test_needs_help_wants_coverage_and_a_bad_reading():
    # Covered the concept, and it went badly — the one case worth an alert.
    assert needs_help(exposure=100, fluency=50) is True
    # Covered it and it went fine.
    assert needs_help(exposure=100, fluency=90) is False
    # Went badly, but they have barely started: nothing to conclude yet, and
    # this is the case that used to flood the page.
    assert needs_help(exposure=20, fluency=20) is False
    # Nothing judgeable yet at all.
    assert needs_help(exposure=0, fluency=None) is False


def test_finishing_everything_slowly_is_never_an_alert():
    """The worst possible completed run of a concept still finishes the work,
    and the page must not tell a teacher to sit with that student."""
    worst = [exercise_score(10_000, 99, 99)] * 4
    assert needs_help(exposure_for(4, 4), fluency_for(worst)) is False


def test_described_model_matches_the_constants():
    """The teacher-facing explanation is generated from the code that scores,
    so it cannot drift from it."""
    model = describe_mastery_model()

    assert model["completed_floor"] == COMPLETED_FLOOR
    assert model["min_assessments"] == MIN_ASSESSMENTS
    assert model["full_marks"] == FULL_MARKS
    assert (
        model["covered_minimum"]
        == EXPOSURE_BANDS[model["covered_band"] - 1]["minimum"]
    )

    # Every band carries the copy the modal renders, and both scales tile
    # 0-100 without a gap or an overlap.
    for key in ("bands", "exposure_bands"):
        assert [band["band"] for band in model[key]] == [1, 2, 3, 4]
        previous_minimum = 101
        for band in model[key]:
            assert band["label"] and band["meaning"]
            assert band["maximum"] == previous_minimum - 1
            previous_minimum = band["minimum"]
        assert previous_minimum == 0
