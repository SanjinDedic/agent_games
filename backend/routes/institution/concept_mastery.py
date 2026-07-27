"""How concept mastery is scored.

Every number a teacher sees on the Concepts tab comes from this module, and
`describe_mastery_model()` hands the same rules to the frontend so the "how is
this calculated?" modal can never drift from the code that calculates it.

The model in one paragraph: an exercise costs a student some *effort* — the
number of goes it took to pass, plus a little for each revealed hint. Low
effort earns full points, high effort earns fewer, and an exercise the student
has attempted but never passed earns none. A concept's score is the mean over
the exercises the student has actually touched, with one override: a student
who has passed *every* exercise tagged with the concept cannot score below the
band-2 floor, however long it took them. That score is then reported as one of
four bands, because a percentage claims a precision this evidence does not
have — the number survives only as a tiebreaker for ordering.
"""

# --- Effort ----------------------------------------------------------------

# A revealed hint is a nudge, not a failed attempt: some students read hints by
# habit. Each one costs half a go, and the total hint cost per exercise is
# capped, so a hint-reader can slip at most one band. Setting HINT_EFFORT_WEIGHT
# to 0 removes hints from the score entirely — which is the intended lever if
# authored hints are ever replaced by AI hints.
HINT_EFFORT_WEIGHT = 0.5
MAX_HINT_EFFORT = 1.0

# (max effort, points) — the first bucket the effort fits into wins.
EFFORT_POINTS = ((1.0, 100), (2.0, 85), (4.0, 70), (7.0, 55))
EFFORT_POINTS_FLOOR = 45
NOT_PASSED_POINTS = 0

# --- Bands -----------------------------------------------------------------

# Passing every exercise for a concept is evidence of understanding whatever it
# cost, so it floors the score into band 2. Nothing else can override a band.
COMPLETION_FLOOR = 60

# Strongest first; `minimum` is inclusive, and the last band must be 0 so every
# score lands somewhere.
BANDS = (
    {
        "band": 1,
        "key": "approaching_mastery",
        "label": "Approaching mastery",
        "minimum": 80,
        "meaning": "Passing these exercises quickly and with little help.",
    },
    {
        "band": 2,
        "key": "showing_understanding",
        "label": "Showing understanding",
        "minimum": 60,
        "meaning": "Getting there, but it is costing them attempts or hints.",
    },
    {
        "band": 3,
        "key": "progressing_slowly",
        "label": "Progressing slowly",
        "minimum": 40,
        "meaning": "Passing some of it the hard way, or stuck on part of it.",
    },
    {
        "band": 4,
        "key": "needs_help",
        "label": "Needs help",
        "minimum": 0,
        "meaning": "Attempted it and is not getting through. Sit with them.",
    },
)

# Bands a teacher is being asked to do something about.
ATTENTION_BANDS = (3, 4)

# --- Confidence ------------------------------------------------------------

# One exercise is an anecdote, not an assessment. A concept needs to come back
# this many times before a reading of it deserves to be stated plainly ("is
# struggling") rather than hedged ("may be struggling"), and a course that tags
# a concept on fewer exercises than this is flagged as under-assessed.
MIN_ASSESSMENTS = 3
CONFIDENCE_MEDIUM = 2


def exercise_points(passed: bool, attempts_to_pass: int, hints: int) -> int:
    """Points for one (student, exercise) pair.

    An exercise that was attempted but never passed scores nothing — that is
    the strongest signal on the page, and softening it would hide the students
    who are actually stuck.
    """
    if not passed:
        return NOT_PASSED_POINTS
    effort = attempts_to_pass + min(hints * HINT_EFFORT_WEIGHT, MAX_HINT_EFFORT)
    for max_effort, points in EFFORT_POINTS:
        if effort <= max_effort:
            return points
    return EFFORT_POINTS_FLOOR


def concept_score(points: list, passed_count: int, exercises_total: int) -> int:
    """A student's score for one concept, from their per-exercise points.

    `points` covers only the exercises they touched; never-attempted work is
    "not reached", not a zero. The completion floor applies when they have
    passed every exercise the concept is tagged on in this classroom.
    """
    score = round(sum(points) / len(points))
    if exercises_total and passed_count == exercises_total:
        return max(score, COMPLETION_FLOOR)
    return score


def band_for(score: int) -> dict:
    """The band record a score falls into. The last band's minimum is 0, so
    this always returns."""
    for band in BANDS:
        if score >= band["minimum"]:
            return band
    return BANDS[-1]


def confidence_for(exercises_touched: int) -> str:
    """How much a cell's reading is worth: "high", "medium" or "low".

    Drives whether the UI says a student *is* struggling with a concept or only
    *may be* — the difference between a teacher trusting the page and learning
    to ignore it.
    """
    if exercises_touched >= MIN_ASSESSMENTS:
        return "high"
    if exercises_touched >= CONFIDENCE_MEDIUM:
        return "medium"
    return "low"


def describe_mastery_model() -> dict:
    """The whole scoring model, JSON-serializable, for the teacher-facing
    "how is this calculated?" modal.

    Built from the constants above rather than written out in prose, so the
    explanation is the implementation.
    """
    ranges = []
    for index, band in enumerate(BANDS):
        upper = 100 if index == 0 else BANDS[index - 1]["minimum"] - 1
        ranges.append({**band, "maximum": upper})

    return {
        "bands": ranges,
        "attention_bands": list(ATTENTION_BANDS),
        "effort_points": [
            {"max_effort": max_effort, "points": points}
            for max_effort, points in EFFORT_POINTS
        ],
        "effort_points_floor": EFFORT_POINTS_FLOOR,
        "not_passed_points": NOT_PASSED_POINTS,
        "hint_effort_weight": HINT_EFFORT_WEIGHT,
        "max_hint_effort": MAX_HINT_EFFORT,
        "completion_floor": COMPLETION_FLOOR,
        "min_assessments": MIN_ASSESSMENTS,
        "confidence_medium": CONFIDENCE_MEDIUM,
    }
