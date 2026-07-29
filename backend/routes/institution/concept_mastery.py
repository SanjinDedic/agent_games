"""How concept mastery is scored.

Every number a teacher sees on the Concepts tab comes from this module, and
`describe_mastery_model()` hands the same rules to the frontend so the "how is
this worked out?" modal can never drift from the code that works it out.

The model in one paragraph. A concept is described by two independent numbers,
because "hasn't done it" and "did it badly" are different problems needing
different responses. **Exposure** is how much of the concept's work the student
has actually finished: completed exercises over the exercises tagged with that
concept. **Fluency** is how the finished work went: a completed exercise starts
at full marks and loses points for taking a long time, for revealed hints and
for a long run of failed goes, and an exercise the student has really had a go
at without passing scores nothing at all. Both are reported as named bands and
drawn as bars. Neither is ever printed as a percentage — counting submissions
does not justify telling a teacher a student is 68% of the way to understanding
dictionaries.
"""

import math

# --- What one completed exercise scores -------------------------------------

FULL_MARKS = 100

# Passing inside this many minutes of the *first submission* is full marks
# however it was done. A student who gets there in five minutes knew it, and
# charging them for the hints they read on the way only teaches them to avoid
# the hints. Note the clock starts at the first submission, not at opening the
# exercise: time spent reading and thinking before having a go is free.
FREE_MINUTES = 5

# Past that, every further block of MINUTES_PER_STEP minutes costs
# TIME_PENALTY_STEP, and the whole time penalty stops at MAX_TIME_PENALTY —
# an hour and a day off the pace are the same message to a teacher.
MINUTES_PER_STEP = 5
TIME_PENALTY_STEP = 5
MAX_TIME_PENALTY = 15

# A revealed hint is a nudge, not a failure: it costs something, but the total
# is capped so a habitual hint-reader who finishes cannot look like a student
# who never got there. Set HINT_PENALTY to 0 to take hints out of the score
# entirely — the intended lever if authored hints become AI hints.
HINT_PENALTY = 5
MAX_HINT_PENALTY = 15

# One flat charge for a long run of failed goes, rather than a per-attempt
# slope: the difference between six goes and seven is noise, the difference
# between three and thirteen is not.
MANY_ATTEMPTS = 5
MANY_ATTEMPTS_PENALTY = 10

# Every completed exercise lands in [COMPLETED_FLOOR, FULL_MARKS]. Finishing
# is worth a lot, and the floor is what says so.
COMPLETED_FLOOR = (
    FULL_MARKS - MAX_TIME_PENALTY - MAX_HINT_PENALTY - MANY_ATTEMPTS_PENALTY
)

# An exercise attempted but never passed scores nothing — but only once the
# student has really had a go at it. Up to and including this many attempts it
# is work in progress and is left out of the average altogether, because a
# student part-way through their second try is not a student in trouble.
NOT_PASSED_POINTS = 0
ATTEMPTS_BEFORE_COUNTED = 2


def time_penalty(minutes_to_pass: float) -> int:
    """Points lost to the clock. Zero inside the free window, then one step per
    started block of minutes beyond it, capped.

    A missing time — data from before the clock was recorded — is treated as
    fast rather than slow: guessing against a student is worse than under-
    reporting, and it only ever makes the page quieter.
    """
    if minutes_to_pass is None or minutes_to_pass <= FREE_MINUTES:
        return 0
    blocks_over = math.ceil((minutes_to_pass - FREE_MINUTES) / MINUTES_PER_STEP)
    return min(blocks_over * TIME_PENALTY_STEP, MAX_TIME_PENALTY)


def exercise_score(minutes_to_pass: float, hints: int, attempts: int) -> int:
    """Points for one *completed* exercise, in [COMPLETED_FLOOR, FULL_MARKS].

    Speed is the headline signal, so a fast pass short-circuits the rest: the
    other two penalties only describe work that was already slow.
    """
    lost = time_penalty(minutes_to_pass)
    if not lost:
        return FULL_MARKS
    lost += min(hints * HINT_PENALTY, MAX_HINT_PENALTY)
    if attempts > MANY_ATTEMPTS:
        lost += MANY_ATTEMPTS_PENALTY
    return FULL_MARKS - lost


def exercise_points(
    passed: bool, attempts: int, hints: int, minutes_to_pass: float
) -> int:
    """What one (student, exercise) pair contributes to fluency, or None to be
    left out of the average.

    Three outcomes: a pass scores on its merits, a genuine unpassed struggle
    scores nothing, and an exercise still in its first couple of goes is not
    judged at all.
    """
    if passed:
        return exercise_score(minutes_to_pass, hints, attempts)
    if attempts > ATTEMPTS_BEFORE_COUNTED:
        return NOT_PASSED_POINTS
    return None


# --- Rolling exercises up to a concept --------------------------------------


def fluency_for(points: list) -> int:
    """Mean score over the exercises that count, or None when none do."""
    scored = [point for point in points if point is not None]
    if not scored:
        return None
    return round(sum(scored) / len(scored))


def exposure_for(completed: int, exercises_total: int) -> int:
    """Share of the concept's exercises the student has finished."""
    if not exercises_total:
        return 0
    return round(completed / exercises_total * 100)


# --- Bands ------------------------------------------------------------------

# Strongest first; `minimum` is inclusive, and the last band must be 0 so every
# value lands somewhere.
FLUENCY_BANDS = (
    {
        "band": 1,
        "key": "fluent",
        "label": "Fluent",
        "minimum": 80,
        "meaning": "Finishing quickly and with little help.",
    },
    {
        "band": 2,
        "key": "showing_understanding",
        "label": "Showing understanding",
        # Derived, not chosen: the worst a student who finishes everything can
        # possibly score. See ATTENTION_BANDS for why that is the right line.
        "minimum": COMPLETED_FLOOR,
        "meaning": "Getting there, at some cost in time, hints or goes.",
    },
    {
        "band": 3,
        "key": "progressing_slowly",
        "label": "Progressing slowly",
        # Half the floor: below this, more than half of the work they have
        # genuinely had a go at is work they never finished.
        "minimum": COMPLETED_FLOOR // 2,
        "meaning": "Finishing the hard way, or not finishing some of it.",
    },
    {
        "band": 4,
        "key": "needs_help",
        "label": "Needs help",
        "minimum": 0,
        "meaning": "Having real goes at this and not getting through it.",
    },
)

EXPOSURE_BANDS = (
    {
        "band": 1,
        "key": "most_or_all",
        "label": "Most or all",
        "minimum": 80,
        "meaning": "Has finished nearly everything that practises this.",
    },
    {
        "band": 2,
        "key": "part_way",
        "label": "Part way",
        "minimum": 40,
        "meaning": "Has finished some of the work on this.",
    },
    {
        "band": 3,
        "key": "just_begun",
        "label": "Just begun",
        "minimum": 1,
        "meaning": "Has finished one or two pieces of it.",
    },
    {
        "band": 4,
        "key": "none_yet",
        "label": "None yet",
        "minimum": 0,
        "meaning": "Nothing that practises this is finished.",
    },
)

# Fluency bands a teacher is being asked to do something about. The boundary is
# COMPLETED_FLOOR by construction: a student whose every completed exercise was
# as costly as an exercise can be still sits exactly on the line, so anything
# below it means work that was never finished at all.
ATTENTION_BANDS = (3, 4)

# The exposure band that counts as having covered a concept. Below it the
# reading is about how much is left, not about how it went, and the page says
# nothing about the student's grasp of it.
COVERED_BAND = 1


def band_for(bands: tuple, value: int) -> dict:
    """The band record a value falls into. The last band's minimum is 0, so
    this always returns."""
    for band in bands:
        if value >= band["minimum"]:
            return band
    return bands[-1]


def fluency_band(fluency: int) -> dict:
    return band_for(FLUENCY_BANDS, fluency) if fluency is not None else None


def exposure_band(exposure: int) -> dict:
    return band_for(EXPOSURE_BANDS, exposure)


def needs_help(exposure: int, fluency: int) -> bool:
    """Whether a (student, concept) pair is worth a teacher's afternoon.

    Both halves are required, and that is the whole of the rule: the student
    has covered the concept, so there is nothing left to simply get on with,
    and the covered work still went badly. A student who has barely started is
    not flagged — there is no evidence yet, and flagging them is how a teacher
    learns to ignore the page.
    """
    if fluency is None:
        return False
    return (
        exposure_band(exposure)["band"] == COVERED_BAND
        and fluency_band(fluency)["band"] in ATTENTION_BANDS
    )


# --- Coverage of the course itself ------------------------------------------

# A concept the course practises fewer times than this is an anecdote, however
# well the student did on it, and the page says so rather than quietly implying
# otherwise.
MIN_ASSESSMENTS = 3


def _with_maxima(bands: tuple) -> list:
    ranges = []
    for index, band in enumerate(bands):
        upper = 100 if index == 0 else bands[index - 1]["minimum"] - 1
        ranges.append({**band, "maximum": upper})
    return ranges


def describe_mastery_model() -> dict:
    """The whole scoring model, JSON-serializable, for the teacher-facing
    "how is this worked out?" modal.

    Built from the constants above rather than written out in prose, so the
    explanation is the implementation.
    """
    return {
        "bands": _with_maxima(FLUENCY_BANDS),
        "exposure_bands": _with_maxima(EXPOSURE_BANDS),
        "attention_bands": list(ATTENTION_BANDS),
        "covered_band": COVERED_BAND,
        "covered_minimum": EXPOSURE_BANDS[COVERED_BAND - 1]["minimum"],
        "full_marks": FULL_MARKS,
        "free_minutes": FREE_MINUTES,
        "minutes_per_step": MINUTES_PER_STEP,
        "time_penalty_step": TIME_PENALTY_STEP,
        "max_time_penalty": MAX_TIME_PENALTY,
        "hint_penalty": HINT_PENALTY,
        "max_hint_penalty": MAX_HINT_PENALTY,
        "many_attempts": MANY_ATTEMPTS,
        "many_attempts_penalty": MANY_ATTEMPTS_PENALTY,
        "completed_floor": COMPLETED_FLOOR,
        "not_passed_points": NOT_PASSED_POINTS,
        "attempts_before_counted": ATTEMPTS_BEFORE_COUNTED,
        "min_assessments": MIN_ASSESSMENTS,
    }
