"""Classroom-scoped progress queries backing the classroom workspace.

Scoping model: a classroom's students are the teams whose *current* league is
the classroom (Team.league_id). Per-student stats are team-lifetime — the same
semantics as the Team Progress page and the submissions viewer
(get_all_submissions_for_league is lifetime too). SubmissionMetadata.league_id
is nullable, so filtering on it would silently diverge from the Submissions
tab. Exercise attempted/passed counts are restricted to exercises of tutorials
attached to the classroom; last-active is not (any activity is activity).
"""

import logging

from sqlalchemy import case
from sqlmodel import Session, func, select

from backend.database.db_models import (Concept, Exercise, ExerciseConcept,
                                        ExerciseHintReveal, ExerciseSubmission,
                                        ExerciseSubmissionMetadata, League,
                                        LeagueTutorial, Lesson, LessonConcept,
                                        Submission, SubmissionMetadata, Team,
                                        Tutorial)
from backend.routes.institution.concept_mastery import (
    MIN_ASSESSMENTS,
    describe_mastery_model,
    exercise_points,
    exposure_band,
    exposure_for,
    fluency_band,
    fluency_for,
    needs_help,
)
from backend.routes.institution.institution_db import InstitutionAccessError, TeamNotFoundError

logger = logging.getLogger(__name__)

# Payload bound for per-team ranking history. Enough for a trend line; the
# full history stays in the DB if a longer view is ever needed.
RANKING_HISTORY_LIMIT = 50


def get_team_by_id(
    session: Session, team_id: int, institution_id: int, is_admin: bool = False
) -> Team:
    """Get a team by ID, ensuring it belongs to the institution (admin bypasses)."""
    team = session.get(Team, team_id)
    if not team:
        raise TeamNotFoundError(f"Team with ID {team_id} not found")
    if not is_admin and team.institution_id != institution_id:
        raise InstitutionAccessError(
            "You don't have permission to access this team"
        )
    return team


def _agent_attempt_stats(session: Session, team_ids: list) -> tuple:
    """Per-team lifetime agent stats: {team_id: (attempts, hints, latest_ts)}
    and {team_id: validated_count}."""
    if not team_ids:
        return {}, {}
    attempt_stats = {
        team_id: (attempts, hints, latest)
        for team_id, attempts, hints, latest in session.exec(
            select(
                SubmissionMetadata.team_id,
                func.count(SubmissionMetadata.id),
                func.sum(
                    case((SubmissionMetadata.hint_included == True, 1), else_=0)  # noqa: E712
                ),
                func.max(SubmissionMetadata.timestamp),
            )
            .where(SubmissionMetadata.team_id.in_(team_ids))
            .group_by(SubmissionMetadata.team_id)
        ).all()
    }
    validated_counts = dict(
        session.exec(
            select(SubmissionMetadata.team_id, func.count(Submission.id))
            .join(Submission, Submission.metadata_id == SubmissionMetadata.id)
            .where(SubmissionMetadata.team_id.in_(team_ids))
            .group_by(SubmissionMetadata.team_id)
        ).all()
    )
    return attempt_stats, validated_counts


def _ranking_histories(session: Session, team_ids: list) -> tuple:
    """One newest-first scan of ranked submissions gives both the capped
    per-team history and the ever-hit-first flag (which must see full
    history, not just the window). Pre-ranking submissions have NULL and are
    skipped. Histories come back oldest -> newest so they read as trends."""
    histories: dict = {}
    achieved_first: set = set()
    if not team_ids:
        return histories, achieved_first
    ranked_rows = session.exec(
        select(
            SubmissionMetadata.team_id, Submission.ranking, Submission.timestamp
        )
        .join(Submission, Submission.metadata_id == SubmissionMetadata.id)
        .where(SubmissionMetadata.team_id.in_(team_ids))
        .where(Submission.ranking.is_not(None))
        .order_by(Submission.timestamp.desc(), Submission.id.desc())
    ).all()
    for team_id, ranking, timestamp in ranked_rows:
        history = histories.setdefault(team_id, [])
        if len(history) < RANKING_HISTORY_LIMIT:
            history.append(
                {"ranking": ranking, "timestamp": timestamp.isoformat()}
            )
        if ranking == 1:
            achieved_first.add(team_id)
    for history in histories.values():
        history.reverse()
    return histories, achieved_first


def _league_exercise_cells(
    session: Session, league_id: int, team_ids: list
) -> tuple:
    """Per (team, exercise) attempt stats restricted to exercises of tutorials
    attached to the league: {(team_id, exercise_id): (attempts, last_ts)} and
    the set of (team_id, exercise_id) pairs with a passed run."""
    if not team_ids:
        return {}, set()
    attempts = {
        (team_id, exercise_id): (count, last_ts)
        for team_id, exercise_id, count, last_ts in session.exec(
            select(
                ExerciseSubmissionMetadata.team_id,
                ExerciseSubmissionMetadata.exercise_id,
                func.count(ExerciseSubmissionMetadata.id),
                func.max(ExerciseSubmissionMetadata.timestamp),
            )
            .join(
                Exercise,
                Exercise.id == ExerciseSubmissionMetadata.exercise_id,
            )
            .join(
                LeagueTutorial,
                LeagueTutorial.tutorial_id == Exercise.tutorial_id,
            )
            .where(LeagueTutorial.league_id == league_id)
            .where(ExerciseSubmissionMetadata.team_id.in_(team_ids))
            .group_by(
                ExerciseSubmissionMetadata.team_id,
                ExerciseSubmissionMetadata.exercise_id,
            )
        ).all()
    }
    passed_pairs = set(
        session.exec(
            select(
                ExerciseSubmissionMetadata.team_id,
                ExerciseSubmissionMetadata.exercise_id,
            )
            .join(
                ExerciseSubmission,
                ExerciseSubmission.metadata_id == ExerciseSubmissionMetadata.id,
            )
            .join(
                Exercise,
                Exercise.id == ExerciseSubmissionMetadata.exercise_id,
            )
            .join(
                LeagueTutorial,
                LeagueTutorial.tutorial_id == Exercise.tutorial_id,
            )
            .where(LeagueTutorial.league_id == league_id)
            .where(ExerciseSubmissionMetadata.team_id.in_(team_ids))
            .where(ExerciseSubmission.passed == True)  # noqa: E712
            .distinct()
        ).all()
    )
    return attempts, passed_pairs


def _league_exercise_effort(
    session: Session, league_id: int, team_ids: list
) -> dict:
    """Per (team, exercise) effort detail for the league's exercises:
    {(team_id, exercise_id): {attempts, attempts_to_pass, passed, crashes,
    minutes_to_pass, last_attempt_at}}.

    _league_exercise_cells answers "did they pass, and how many goes in
    total"; mastery needs "how many goes did it take *to* pass" and "how long
    did it take", neither of which an aggregate can give. So this walks the
    attempts in order instead. The join to ExerciseSubmission is an OUTER join
    on purpose: metadata with no submission child means the code never ran at
    all (record_failed_exercise_submission), which is a struggle signal of its
    own and would otherwise vanish from the counts.

    `minutes_to_pass` runs from the first submission to the passing one, not
    from opening the exercise — the server never sees the opening. Reading the
    problem and thinking before the first go is therefore free, which is the
    right bias: it is the flailing after a first attempt that this is trying to
    measure.

    Folding in Python rather than writing window functions keeps this readable
    and costs little — a classroom is tens of students over tens of exercises.
    """
    if not team_ids:
        return {}
    rows = session.exec(
        select(
            ExerciseSubmissionMetadata.team_id,
            ExerciseSubmissionMetadata.exercise_id,
            ExerciseSubmissionMetadata.timestamp,
            ExerciseSubmission.passed,
        )
        .join(
            ExerciseSubmission,
            ExerciseSubmission.metadata_id == ExerciseSubmissionMetadata.id,
            isouter=True,
        )
        .join(Exercise, Exercise.id == ExerciseSubmissionMetadata.exercise_id)
        .join(
            LeagueTutorial, LeagueTutorial.tutorial_id == Exercise.tutorial_id
        )
        .where(LeagueTutorial.league_id == league_id)
        .where(ExerciseSubmissionMetadata.team_id.in_(team_ids))
        .order_by(
            ExerciseSubmissionMetadata.team_id,
            ExerciseSubmissionMetadata.exercise_id,
            ExerciseSubmissionMetadata.timestamp,
            ExerciseSubmissionMetadata.id,
        )
    ).all()

    effort: dict = {}
    for team_id, exercise_id, timestamp, passed in rows:
        cell = effort.setdefault(
            (team_id, exercise_id),
            {
                "attempts": 0,
                "attempts_to_pass": None,
                "passed": False,
                "crashes": 0,
                "first_attempt_at": timestamp,
                "minutes_to_pass": None,
                "last_attempt_at": None,
            },
        )
        cell["attempts"] += 1
        if passed is None:
            cell["crashes"] += 1
        elif passed and not cell["passed"]:
            # Rows arrive oldest first, so the first pass we see is the first
            # pass there was, the running count is the goes it took, and the
            # gap back to the first row is how long it took.
            cell["passed"] = True
            cell["attempts_to_pass"] = cell["attempts"]
            cell["minutes_to_pass"] = (
                timestamp - cell["first_attempt_at"]
            ).total_seconds() / 60
        cell["last_attempt_at"] = timestamp
    return effort


def _league_hint_reveals(
    session: Session, league_id: int, team_ids: list
) -> dict:
    """{(team_id, exercise_id): hints revealed} for the league's exercises."""
    if not team_ids:
        return {}
    return {
        (team_id, exercise_id): count
        for team_id, exercise_id, count in session.exec(
            select(
                ExerciseHintReveal.team_id,
                ExerciseHintReveal.exercise_id,
                func.count(ExerciseHintReveal.id),
            )
            .join(Exercise, Exercise.id == ExerciseHintReveal.exercise_id)
            .join(
                LeagueTutorial,
                LeagueTutorial.tutorial_id == Exercise.tutorial_id,
            )
            .where(LeagueTutorial.league_id == league_id)
            .where(ExerciseHintReveal.team_id.in_(team_ids))
            .group_by(
                ExerciseHintReveal.team_id, ExerciseHintReveal.exercise_id
            )
        ).all()
    }


def _league_concept_tags(session: Session, league_id: int) -> tuple:
    """Concepts tagged on the league's exercises: the Concept rows, and
    {concept_id: [exercise ids]} in curriculum order.

    `order_index` is only unique within a tutorial, so each exercise carries
    its tutorial too — a league can have several tutorials attached, and
    comparing bare order_index values across them would interleave the
    curriculum.
    """
    rows = session.exec(
        select(
            Concept,
            Exercise.id,
            Exercise.title,
            Exercise.order_index,
            Exercise.tutorial_id,
        )
        .join(ExerciseConcept, ExerciseConcept.concept_id == Concept.id)
        .join(Exercise, Exercise.id == ExerciseConcept.exercise_id)
        .join(
            LeagueTutorial, LeagueTutorial.tutorial_id == Exercise.tutorial_id
        )
        .where(LeagueTutorial.league_id == league_id)
        .order_by(Exercise.tutorial_id, Exercise.order_index)
    ).all()

    concepts: dict = {}
    exercises_by_concept: dict = {}
    for concept, exercise_id, exercise_title, order_index, tutorial_id in rows:
        concepts[concept.id] = concept
        exercises_by_concept.setdefault(concept.id, []).append(
            {
                "id": exercise_id,
                "title": exercise_title,
                "order_index": order_index,
                "tutorial_id": tutorial_id,
            }
        )
    return concepts, exercises_by_concept


def _lesson_slugs_by_concept(session: Session, concept_ids: list) -> dict:
    """{concept_id: lesson slug} — the remediation link behind each concept.
    A concept with several lessons keeps the first by slug, deterministically."""
    if not concept_ids:
        return {}
    slugs: dict = {}
    for concept_id, slug in session.exec(
        select(LessonConcept.concept_id, Lesson.slug)
        .join(Lesson, Lesson.id == LessonConcept.lesson_id)
        .where(LessonConcept.concept_id.in_(concept_ids))
        .order_by(Lesson.slug)
    ).all():
        slugs.setdefault(concept_id, slug)
    return slugs


def _latest_exercise_activity(session: Session, team_ids: list) -> dict:
    """{team_id: latest exercise attempt timestamp} across ALL exercises."""
    if not team_ids:
        return {}
    return dict(
        session.exec(
            select(
                ExerciseSubmissionMetadata.team_id,
                func.max(ExerciseSubmissionMetadata.timestamp),
            )
            .where(ExerciseSubmissionMetadata.team_id.in_(team_ids))
            .group_by(ExerciseSubmissionMetadata.team_id)
        ).all()
    )


def _league_tutorials(session: Session, league_id: int) -> list:
    """Tutorials attached to a league, in tutorial-id order."""
    return session.exec(
        select(Tutorial)
        .join(LeagueTutorial, LeagueTutorial.tutorial_id == Tutorial.id)
        .where(LeagueTutorial.league_id == league_id)
        .order_by(Tutorial.id)
    ).all()


def get_classroom_progress(session: Session, league: League) -> dict:
    """Per-student roster stats for one classroom: lifetime agent submission
    stats, ranking trend, and exercise completion against the classroom's
    attached tutorials."""
    teams = session.exec(
        select(Team).where(Team.league_id == league.id).order_by(Team.name)
    ).all()
    team_ids = [team.id for team in teams]

    attempt_stats, validated_counts = _agent_attempt_stats(session, team_ids)
    histories, achieved_first = _ranking_histories(session, team_ids)
    exercise_activity = _latest_exercise_activity(session, team_ids)
    cell_attempts, passed_pairs = _league_exercise_cells(
        session, league.id, team_ids
    )

    exercises_total = session.exec(
        select(func.count(Exercise.id))
        .join(LeagueTutorial, LeagueTutorial.tutorial_id == Exercise.tutorial_id)
        .where(LeagueTutorial.league_id == league.id)
    ).one()

    attempted_by_team: dict = {}
    for team_id, _exercise_id in cell_attempts:
        attempted_by_team[team_id] = attempted_by_team.get(team_id, 0) + 1
    passed_by_team: dict = {}
    for team_id, _exercise_id in passed_pairs:
        passed_by_team[team_id] = passed_by_team.get(team_id, 0) + 1

    team_rows = []
    for team in teams:
        attempts, hints, latest_agent = attempt_stats.get(team.id, (0, 0, None))
        latest_exercise = exercise_activity.get(team.id)
        candidates = [ts for ts in (latest_agent, latest_exercise) if ts]
        last_active = max(candidates) if candidates else None
        team_rows.append(
            {
                "id": team.id,
                "name": team.name,
                "school": team.school_name,
                "total_attempts": attempts,
                "validated_submissions": validated_counts.get(team.id, 0),
                "hints_used": hints,
                "latest_agent_submission": (
                    latest_agent.isoformat() if latest_agent else None
                ),
                "latest_exercise_activity": (
                    latest_exercise.isoformat() if latest_exercise else None
                ),
                "last_active": last_active.isoformat() if last_active else None,
                "ranking_history": histories.get(team.id, []),
                "achieved_first": team.id in achieved_first,
                "exercises_attempted": attempted_by_team.get(team.id, 0),
                "exercises_passed": passed_by_team.get(team.id, 0),
                "exercises_total": exercises_total,
            }
        )

    return {
        "league": {
            "id": league.id,
            "name": league.name,
            "game": league.game,
            "expiry_date": (
                league.expiry_date.isoformat() if league.expiry_date else None
            ),
            "signup_link": league.signup_link,
        },
        "teams": team_rows,
    }


def get_classroom_tutorial_matrix(session: Session, league: League) -> dict:
    """Student x exercise grid per tutorial attached to the classroom.

    Untouched cells are omitted; the client renders absence as untouched.
    """
    teams = session.exec(
        select(Team).where(Team.league_id == league.id).order_by(Team.name)
    ).all()
    team_ids = [team.id for team in teams]
    cell_attempts, passed_pairs = _league_exercise_cells(
        session, league.id, team_ids
    )

    tutorials = []
    for tutorial in _league_tutorials(session, league.id):
        cells = []
        for exercise in tutorial.exercises:
            for team_id in team_ids:
                key = (team_id, exercise.id)
                if key not in cell_attempts:
                    continue
                count, last_ts = cell_attempts[key]
                cells.append(
                    {
                        "team_id": team_id,
                        "exercise_id": exercise.id,
                        "status": (
                            "passed" if key in passed_pairs else "attempted"
                        ),
                        "attempts": count,
                        "last_attempt_at": (
                            last_ts.isoformat() if last_ts else None
                        ),
                    }
                )
        tutorials.append(
            {
                "id": tutorial.id,
                "title": tutorial.title,
                "exercises": [
                    {
                        "id": exercise.id,
                        "title": exercise.title,
                        "order_index": exercise.order_index,
                    }
                    for exercise in tutorial.exercises
                ],
                "cells": cells,
            }
        )

    return {
        "league": {"id": league.id, "name": league.name},
        "teams": [{"id": team.id, "name": team.name} for team in teams],
        "tutorials": tutorials,
    }


def get_classroom_concept_matrix(session: Session, league: League) -> dict:
    """Student x concept mastery grid for one classroom.

    Rolls every exercise attempt up to the concepts its exercise is tagged
    with, so a teacher sees what to reteach rather than which exercise numbers
    went badly. Every cell carries two numbers — `exposure`, how much of the
    concept's work the student has finished, and `fluency`, how that finished
    work went — plus the band each falls into. Scoring lives in
    concept_mastery.py and ships with the payload (`scoring`) so the
    teacher-facing explanation cannot drift from it.

    "Not reached" cells are omitted, as in the tutorial matrix — the client
    renders absence. A cell exists as soon as a student has attempted one of
    the concept's exercises, but its `fluency` stays null until something they
    did there can be judged, so an in-progress first attempt shows coverage
    without pretending to a verdict.

    Two coverage figures are reported deliberately, because an incomplete map
    must never read as a confident one: `untagged_exercises` is how much of the
    classroom's content this map ignores, and each concept's `under_assessed`
    flag marks the ones tested too few times for their row to mean much.
    """
    teams = session.exec(
        select(Team).where(Team.league_id == league.id).order_by(Team.name)
    ).all()
    team_ids = [team.id for team in teams]

    concepts, exercises_by_concept = _league_concept_tags(session, league.id)
    lesson_slugs = _lesson_slugs_by_concept(session, list(concepts))
    effort = _league_exercise_effort(session, league.id, team_ids)
    hints = _league_hint_reveals(session, league.id, team_ids)

    exercises_total = session.exec(
        select(func.count(Exercise.id))
        .join(LeagueTutorial, LeagueTutorial.tutorial_id == Exercise.tutorial_id)
        .where(LeagueTutorial.league_id == league.id)
    ).one()
    tagged_exercise_ids = {
        exercise["id"]
        for exercises in exercises_by_concept.values()
        for exercise in exercises
    }

    cells = []
    # {concept_id: [exposure, ...]} and {concept_id: [fluency, ...]} over the
    # students who have touched it, for the class figures beside the matrix.
    class_exposure: dict = {}
    class_fluency: dict = {}
    attention_counts: dict = {}
    for concept_id, exercises in exercises_by_concept.items():
        for team in teams:
            points = []
            attempted_count = 0
            passed_count = 0
            attempts_total = 0
            hints_total = 0
            tries_to_pass = []
            minutes = []
            last_attempt = None
            for exercise in exercises:
                cell = effort.get((team.id, exercise["id"]))
                if not cell:
                    continue
                attempted_count += 1
                exercise_hints = hints.get((team.id, exercise["id"]), 0)
                points.append(
                    exercise_points(
                        cell["passed"],
                        cell["attempts_to_pass"] or cell["attempts"],
                        exercise_hints,
                        cell["minutes_to_pass"],
                    )
                )
                attempts_total += cell["attempts"]
                hints_total += exercise_hints
                if cell["passed"]:
                    passed_count += 1
                    tries_to_pass.append(cell["attempts_to_pass"])
                    if cell["minutes_to_pass"] is not None:
                        minutes.append(cell["minutes_to_pass"])
                if cell["last_attempt_at"] and (
                    last_attempt is None
                    or cell["last_attempt_at"] > last_attempt
                ):
                    last_attempt = cell["last_attempt_at"]

            if not attempted_count:
                continue  # not reached — the client renders absence

            exposure = exposure_for(passed_count, len(exercises))
            fluency = fluency_for(points)
            exposure_row = exposure_band(exposure)
            fluency_row = fluency_band(fluency)

            class_exposure.setdefault(concept_id, []).append(exposure)
            if fluency is not None:
                class_fluency.setdefault(concept_id, []).append(fluency)
            if needs_help(exposure, fluency):
                attention_counts[concept_id] = (
                    attention_counts.get(concept_id, 0) + 1
                )
            cells.append(
                {
                    "team_id": team.id,
                    "concept_id": concept_id,
                    # The two figures the whole tab is built on. They drive the
                    # bar widths; the client never prints them as numbers.
                    "exposure": exposure,
                    "fluency": fluency,
                    "exposure_band": exposure_row["band"],
                    "exposure_band_key": exposure_row["key"],
                    "band": fluency_row["band"] if fluency_row else None,
                    "band_key": fluency_row["key"] if fluency_row else None,
                    "needs_help": needs_help(exposure, fluency),
                    # The evidence line on every card: what they have had a go
                    # at, and what they have finished, out of the whole concept.
                    "exercises_attempted": attempted_count,
                    "exercises_passed": passed_count,
                    "exercises_total": len(exercises),
                    "attempts": attempts_total,
                    "avg_attempts_to_pass": (
                        round(sum(tries_to_pass) / len(tries_to_pass), 1)
                        if tries_to_pass
                        else None
                    ),
                    "avg_minutes_to_pass": (
                        round(sum(minutes) / len(minutes)) if minutes else None
                    ),
                    "hints_used": hints_total,
                    "last_attempt_at": (
                        last_attempt.isoformat() if last_attempt else None
                    ),
                }
            )

    concept_rows = []
    # {concept_id: (tutorial_id, order_index)} of where the concept is first
    # taught — order_index restarts per tutorial, so both halves are needed.
    first_taught = {}
    for concept_id, concept in concepts.items():
        exposures = class_exposure.get(concept_id, [])
        fluencies = class_fluency.get(concept_id, [])
        exercises = exercises_by_concept[concept_id]
        # The class is one average student: the mean of what everyone who has
        # touched the concept has covered, and of how their work went. The
        # reteach rule is then the same test applied to that student, so a
        # teacher only has to learn the rule once.
        avg_exposure = (
            round(sum(exposures) / len(exposures)) if exposures else None
        )
        avg_fluency = (
            round(sum(fluencies) / len(fluencies)) if fluencies else None
        )
        exposure_row = (
            exposure_band(avg_exposure) if avg_exposure is not None else None
        )
        fluency_row = fluency_band(avg_fluency)
        first_taught[concept_id] = min(
            (exercise["tutorial_id"], exercise["order_index"])
            for exercise in exercises
        )
        concept_rows.append(
            {
                "id": concept_id,
                "slug": concept.slug,
                "name": concept.name,
                "description": concept.description,
                "category": concept.category,
                "lesson_slug": lesson_slugs.get(concept_id),
                # Curriculum order: where this concept is first taught.
                "order_index": first_taught[concept_id][1],
                "exercises": exercises,
                "exercises_total": len(exercises),
                # Too few exercises for this row to be evidence rather than an
                # anecdote — the tab says so rather than quietly implying otherwise.
                "under_assessed": len(exercises) < MIN_ASSESSMENTS,
                "class_exposure": avg_exposure,
                "class_fluency": avg_fluency,
                "exposure_band": exposure_row["band"] if exposure_row else None,
                "exposure_band_key": (
                    exposure_row["key"] if exposure_row else None
                ),
                "band": fluency_row["band"] if fluency_row else None,
                "band_key": fluency_row["key"] if fluency_row else None,
                # Covered by the class as a whole, and still going badly: the
                # only thing on this page that asks a teacher to reteach.
                "reteach": (
                    avg_exposure is not None
                    and needs_help(avg_exposure, avg_fluency)
                ),
                "reached": len(exposures),
                "needs_attention": attention_counts.get(concept_id, 0),
            }
        )
    concept_rows.sort(
        key=lambda row: (row["category"] or "", first_taught[row["id"]])
    )

    return {
        "league": {"id": league.id, "name": league.name},
        "teams": [{"id": team.id, "name": team.name} for team in teams],
        "concepts": concept_rows,
        "cells": cells,
        # Who to help, worst first: the weakest fluency, then the most work
        # covered to arrive at it. The client turns this into sentences.
        "attention": [
            {
                "team_id": cell["team_id"],
                "concept_id": cell["concept_id"],
                "band": cell["band"],
            }
            for cell in sorted(
                (cell for cell in cells if cell["needs_help"]),
                key=lambda cell: (cell["fluency"], -cell["exposure"]),
            )
        ],
        "untagged_exercises": exercises_total - len(tagged_exercise_ids),
        "exercises_total": exercises_total,
        "under_assessed_concepts": sum(
            1 for row in concept_rows if row["under_assessed"]
        ),
        "scoring": describe_mastery_model(),
    }


def get_student_summary(session: Session, team: Team) -> dict:
    """Drill-down header data for one student: identity, lifetime agent stats
    with ranking trend, and per-exercise tutorial status for the tutorials
    attached to the student's current classroom (untouched exercises
    included, unlike the matrix)."""
    attempt_stats, validated_counts = _agent_attempt_stats(session, [team.id])
    histories, achieved_first = _ranking_histories(session, [team.id])
    attempts, hints, latest_agent = attempt_stats.get(team.id, (0, 0, None))
    latest_exercise = _latest_exercise_activity(session, [team.id]).get(team.id)
    candidates = [ts for ts in (latest_agent, latest_exercise) if ts]
    last_active = max(candidates) if candidates else None

    tutorials = []
    if team.league_id:
        cell_attempts, passed_pairs = _league_exercise_cells(
            session, team.league_id, [team.id]
        )
        for tutorial in _league_tutorials(session, team.league_id):
            exercises = []
            for exercise in tutorial.exercises:
                key = (team.id, exercise.id)
                count, last_ts = cell_attempts.get(key, (0, None))
                if key in passed_pairs:
                    status = "passed"
                elif count:
                    status = "attempted"
                else:
                    status = "untouched"
                exercises.append(
                    {
                        "id": exercise.id,
                        "title": exercise.title,
                        "order_index": exercise.order_index,
                        "status": status,
                        "attempts": count,
                        "last_attempt_at": (
                            last_ts.isoformat() if last_ts else None
                        ),
                    }
                )
            tutorials.append(
                {
                    "id": tutorial.id,
                    "title": tutorial.title,
                    "exercises": exercises,
                }
            )

    return {
        "team": {
            "id": team.id,
            "name": team.name,
            "school": team.school_name,
            "league_id": team.league_id,
            "league_name": team.league.name if team.league else None,
            "created_at": (
                team.created_at.isoformat() if team.created_at else None
            ),
        },
        "agent": {
            "total_attempts": attempts,
            "validated_submissions": validated_counts.get(team.id, 0),
            "hints_used": hints,
            "latest_submission": (
                latest_agent.isoformat() if latest_agent else None
            ),
            "ranking_history": histories.get(team.id, []),
            "achieved_first": team.id in achieved_first,
        },
        "last_active": last_active.isoformat() if last_active else None,
        "tutorials": tutorials,
    }


def get_student_agent_submissions(session: Session, team: Team) -> dict:
    """One student's full validated agent submission history, oldest first
    (matching the submission viewer's prev/next indexing)."""
    rows = session.exec(
        select(Submission, SubmissionMetadata)
        .join(SubmissionMetadata, Submission.metadata_id == SubmissionMetadata.id)
        .where(SubmissionMetadata.team_id == team.id)
        .order_by(Submission.timestamp.asc(), Submission.id.asc())
    ).all()

    return {
        "team": {"id": team.id, "name": team.name},
        "submissions": [
            {
                "id": sub.id,
                "code": sub.code,
                "timestamp": sub.timestamp.isoformat(),
                "duration_ms": meta.duration_ms,
                "ranking": sub.ranking,
                "league_id": meta.league_id,
            }
            for sub, meta in rows
        ],
    }
