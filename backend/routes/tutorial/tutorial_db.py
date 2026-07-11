import logging
from datetime import timedelta
from typing import Optional

from sqlmodel import Session, func, select

from backend.database.db_models import (
    Exercise,
    ExerciseSubmission,
    ExerciseSubmissionMetadata,
    Tutorial,
)
# Reused so the existing 429 handler in api.py covers exercise rate limiting.
from backend.routes.user.user_db import SubmissionLimitExceededError
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)


class TutorialNotFoundError(Exception):
    """Raised when a tutorial is not found (maps to HTTP 404)."""

    pass


class ExerciseNotFoundError(Exception):
    """Raised when an exercise is not found (maps to HTTP 404)."""

    pass


def allow_exercise_submission(session: Session, team_id: int) -> bool:
    """Check if team is allowed to submit an exercise (rate limiting).

    Same 5/minute budget as agent submissions, counted separately so tutorial
    practice doesn't consume agent submission attempts (and vice versa).
    """
    one_minute_ago = utc_now() - timedelta(minutes=1)
    recent_submissions = session.exec(
        select(ExerciseSubmissionMetadata)
        .where(ExerciseSubmissionMetadata.team_id == team_id)
        .where(ExerciseSubmissionMetadata.timestamp >= one_minute_ago)
    ).all()

    max_submissions = 5
    if len(recent_submissions) >= max_submissions:
        raise SubmissionLimitExceededError(
            f"You can only make {max_submissions} submissions per minute."
        )
    return True


def get_exercise_by_id(session: Session, exercise_id: int) -> Exercise:
    exercise = session.get(Exercise, exercise_id)
    if not exercise:
        raise ExerciseNotFoundError(f"Exercise with ID {exercise_id} not found")
    return exercise


def get_tutorials(session: Session) -> dict:
    """List all tutorials with their exercise counts."""
    tutorials = session.exec(select(Tutorial).order_by(Tutorial.id)).all()
    counts = dict(
        session.exec(
            select(Exercise.tutorial_id, func.count(Exercise.id)).group_by(
                Exercise.tutorial_id
            )
        ).all()
    )
    return {
        "tutorials": [
            {
                "id": tutorial.id,
                "title": tutorial.title,
                "description": tutorial.description,
                "exercise_count": counts.get(tutorial.id, 0),
            }
            for tutorial in tutorials
        ]
    }


def get_tutorial_with_exercises(session: Session, tutorial_id: int) -> dict:
    """One tutorial with its exercises in order.

    Test cases and the entry-function name stay server-side: the student sees
    them through the problem markdown and the per-test feedback, not the raw
    definition.
    """
    tutorial = session.get(Tutorial, tutorial_id)
    if not tutorial:
        raise TutorialNotFoundError(f"Tutorial with ID {tutorial_id} not found")

    return {
        "id": tutorial.id,
        "title": tutorial.title,
        "description": tutorial.description,
        "exercises": [
            {
                "id": exercise.id,
                "title": exercise.title,
                "order_index": exercise.order_index,
                "problem_markdown": exercise.problem_markdown,
                "starter_code": exercise.starter_code,
            }
            for exercise in tutorial.exercises
        ],
    }


def get_tutorial_progress(
    session: Session, team_id: int, tutorial_id: int
) -> dict:
    """One team's progress through a tutorial, one row per exercise in order.

    An exercise is `attempted` once any submission attempt exists (including
    ones whose code never ran) and `passed` once any stored run passed.
    """
    tutorial = session.get(Tutorial, tutorial_id)
    if not tutorial:
        raise TutorialNotFoundError(f"Tutorial with ID {tutorial_id} not found")

    attempted_ids = set(
        session.exec(
            select(ExerciseSubmissionMetadata.exercise_id)
            .join(
                Exercise,
                Exercise.id == ExerciseSubmissionMetadata.exercise_id,
            )
            .where(Exercise.tutorial_id == tutorial_id)
            .where(ExerciseSubmissionMetadata.team_id == team_id)
            .distinct()
        ).all()
    )
    passed_ids = set(
        session.exec(
            select(ExerciseSubmissionMetadata.exercise_id)
            .join(
                ExerciseSubmission,
                ExerciseSubmission.metadata_id == ExerciseSubmissionMetadata.id,
            )
            .join(
                Exercise,
                Exercise.id == ExerciseSubmissionMetadata.exercise_id,
            )
            .where(Exercise.tutorial_id == tutorial_id)
            .where(ExerciseSubmissionMetadata.team_id == team_id)
            .where(ExerciseSubmission.passed == True)  # noqa: E712
            .distinct()
        ).all()
    )

    return {
        "progress": [
            {
                "exercise_id": exercise.id,
                "attempted": exercise.id in attempted_ids,
                "passed": exercise.id in passed_ids,
            }
            for exercise in tutorial.exercises
        ]
    }


def record_failed_exercise_submission(
    session: Session,
    team_id: int,
    exercise_id: int,
    duration_ms: Optional[float] = None,
) -> int:
    """Record an attempt whose code never produced test results. Code is not stored."""
    meta = ExerciseSubmissionMetadata(
        team_id=team_id,
        exercise_id=exercise_id,
        timestamp=utc_now(),
        duration_ms=duration_ms,
    )
    session.add(meta)
    session.commit()
    return meta.id


def save_exercise_submission(
    session: Session,
    code: str,
    team_id: int,
    exercise_id: int,
    passed: bool,
    test_results: list,
    duration_ms: Optional[float] = None,
) -> int:
    """Record an attempt that ran: metadata row plus linked code+results row."""
    now = utc_now()
    meta = ExerciseSubmissionMetadata(
        team_id=team_id,
        exercise_id=exercise_id,
        timestamp=now,
        duration_ms=duration_ms,
    )
    session.add(meta)
    session.flush()
    db_submission = ExerciseSubmission(
        code=code,
        timestamp=now,
        passed=passed,
        test_results=test_results,
        metadata_id=meta.id,
    )
    session.add(db_submission)
    session.commit()
    return db_submission.id


def get_latest_exercise_submission(
    session: Session, team_id: int, exercise_id: int
) -> dict:
    """Latest stored submission for one team+exercise (nulls when none exists)."""
    submission = session.exec(
        select(ExerciseSubmission)
        .join(
            ExerciseSubmissionMetadata,
            ExerciseSubmission.metadata_id == ExerciseSubmissionMetadata.id,
        )
        .where(ExerciseSubmissionMetadata.team_id == team_id)
        .where(ExerciseSubmissionMetadata.exercise_id == exercise_id)
        .order_by(ExerciseSubmission.timestamp.desc())
        .limit(1)
    ).first()

    if not submission:
        return {"code": None, "passed": None, "test_results": []}
    return {
        "code": submission.code,
        "passed": submission.passed,
        "test_results": submission.test_results,
    }


def get_exercise_submission_history(
    session: Session, team_id: int, exercise_id: int
) -> list:
    """Full submission history for one team+exercise, newest first."""
    rows = session.exec(
        select(ExerciseSubmission, ExerciseSubmissionMetadata)
        .join(
            ExerciseSubmissionMetadata,
            ExerciseSubmission.metadata_id == ExerciseSubmissionMetadata.id,
        )
        .where(ExerciseSubmissionMetadata.team_id == team_id)
        .where(ExerciseSubmissionMetadata.exercise_id == exercise_id)
        .order_by(ExerciseSubmission.timestamp.desc())
    ).all()

    return [
        {
            "id": sub.id,
            "code": sub.code,
            "timestamp": sub.timestamp.isoformat(),
            "passed": sub.passed,
            "duration_ms": meta.duration_ms,
        }
        for sub, meta in rows
    ]
