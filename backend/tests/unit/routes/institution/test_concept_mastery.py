"""The concept mastery scoring model, pinned without a database.

The endpoint test covers the rollup; this covers the arithmetic itself, so a
threshold cannot be changed without a test saying what it means.
"""

import pytest

from backend.routes.institution.concept_mastery import (
    BANDS,
    COMPLETION_FLOOR,
    MAX_HINT_EFFORT,
    MIN_ASSESSMENTS,
    NOT_PASSED_POINTS,
    band_for,
    concept_score,
    confidence_for,
    describe_mastery_model,
    exercise_points,
)


@pytest.mark.parametrize(
    "attempts_to_pass,hints,expected",
    [
        (1, 0, 100),  # first go, no help
        (1, 1, 85),   # a hint costs half a go, so this drops one bucket
        (1, 2, 85),   # ...and two hints reach the cap, costing no more
        (1, 9, 85),   # hint-reading cannot cost more than one whole go
        (2, 0, 85),
        (2, 1, 70),
        (4, 0, 70),
        (5, 0, 55),
        (7, 0, 55),
        (8, 0, 45),
        (40, 0, 45),  # the floor: a pass is still worth more than a non-pass
    ],
)
def test_exercise_points(attempts_to_pass, hints, expected):
    assert exercise_points(True, attempts_to_pass, hints) == expected


def test_hints_cost_at_most_one_go():
    """The cap is the whole point: some students read hints by habit, and that
    must not read the same as failing repeatedly."""
    many_hints = exercise_points(True, 1, 20)
    one_extra_go = exercise_points(True, 2, 0)
    assert many_hints == one_extra_go
    assert MAX_HINT_EFFORT == 1.0


def test_not_passing_scores_nothing():
    """However many goes it took, never getting there is the strongest signal
    on the page and is not softened."""
    assert exercise_points(False, 0, 0) == NOT_PASSED_POINTS
    assert exercise_points(False, 12, 5) == NOT_PASSED_POINTS


def test_concept_score_averages_touched_exercises():
    # Two exercises: one clean pass, one never passed.
    assert concept_score([100, 0], passed_count=1, exercises_total=2) == 50


def test_completing_every_exercise_floors_at_band_two():
    """Finishing all the work counts, whatever it cost — the rule that stops
    the metric punishing a student who got there the slow way."""
    slowest = [exercise_points(True, 40, 9)] * 3
    assert max(slowest) < COMPLETION_FLOOR

    scored = concept_score(slowest, passed_count=3, exercises_total=3)
    assert scored == COMPLETION_FLOOR
    assert band_for(scored)["band"] == 2


def test_floor_needs_every_exercise_not_just_the_touched_ones():
    """Passing everything they have attempted is not the same as passing
    everything the concept is taught on."""
    assert concept_score([45], passed_count=1, exercises_total=3) == 45


def test_bands_cover_every_score():
    assert [band["band"] for band in BANDS] == [1, 2, 3, 4]
    assert band_for(100)["key"] == "approaching_mastery"
    assert band_for(80)["key"] == "approaching_mastery"
    assert band_for(79)["key"] == "showing_understanding"
    assert band_for(60)["key"] == "showing_understanding"
    assert band_for(59)["key"] == "progressing_slowly"
    assert band_for(40)["key"] == "progressing_slowly"
    assert band_for(39)["key"] == "needs_help"
    assert band_for(0)["key"] == "needs_help"


def test_confidence_follows_how_often_the_concept_came_back():
    assert confidence_for(1) == "low"
    assert confidence_for(2) == "medium"
    assert confidence_for(MIN_ASSESSMENTS) == "high"
    assert confidence_for(MIN_ASSESSMENTS + 5) == "high"


def test_described_model_matches_the_constants():
    """The teacher-facing explanation is generated from the code that scores,
    so it cannot drift from it."""
    model = describe_mastery_model()

    assert [band["band"] for band in model["bands"]] == [1, 2, 3, 4]
    assert model["completion_floor"] == COMPLETION_FLOOR
    assert model["min_assessments"] == MIN_ASSESSMENTS

    # Every band carries the copy the modal renders, and the ranges tile 0-100
    # without a gap or an overlap.
    previous_minimum = 101
    for band in model["bands"]:
        assert band["label"] and band["meaning"]
        assert band["maximum"] == previous_minimum - 1
        previous_minimum = band["minimum"]
    assert previous_minimum == 0
