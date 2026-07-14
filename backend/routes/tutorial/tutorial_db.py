import logging
from datetime import timedelta
from typing import Optional

from sqlmodel import Session, func, select

from backend.database.db_models import (
    Exercise,
    ExerciseSubmission,
    ExerciseSubmissionMetadata,
    LeagueTutorial,
    Team,
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


class TutorialExistsError(Exception):
    """Raised when a tutorial title is already taken (maps to HTTP 409)."""

    pass


class ExerciseReorderError(Exception):
    """Raised when a reorder request doesn't match the tutorial's exercises
    (maps to HTTP 400)."""

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


def get_team_league_id(session: Session, team_id: int) -> Optional[int]:
    """The league a team currently belongs to, resolved from the DB (not the
    token) so a mid-session league move takes effect immediately."""
    team = session.get(Team, team_id)
    return team.league_id if team else None


def is_tutorial_in_league(
    session: Session, tutorial_id: int, league_id: Optional[int]
) -> bool:
    if league_id is None:
        return False
    return (
        session.exec(
            select(LeagueTutorial)
            .where(LeagueTutorial.tutorial_id == tutorial_id)
            .where(LeagueTutorial.league_id == league_id)
        ).first()
        is not None
    )


def assert_tutorial_in_team_league(
    session: Session, tutorial_id: int, team_id: int
) -> None:
    """404 when the tutorial isn't attached to the team's league — the same
    response as a nonexistent id, so students can't probe other leagues'
    content."""
    league_id = get_team_league_id(session, team_id)
    if not is_tutorial_in_league(session, tutorial_id, league_id):
        raise TutorialNotFoundError(f"Tutorial with ID {tutorial_id} not found")


def assert_exercise_in_team_league(
    session: Session, exercise: Exercise, team_id: int
) -> None:
    """Exercise-flavoured twin of assert_tutorial_in_team_league."""
    league_id = get_team_league_id(session, team_id)
    if not is_tutorial_in_league(session, exercise.tutorial_id, league_id):
        raise ExerciseNotFoundError(f"Exercise with ID {exercise.id} not found")


def get_tutorials(session: Session, league_id: Optional[int] = None) -> dict:
    """List tutorials with their exercise counts.

    With a league_id, only tutorials attached to that league (the team view);
    without one, the full library (admin/institution view)."""
    query = select(Tutorial).order_by(Tutorial.id)
    if league_id is not None:
        query = query.join(
            LeagueTutorial, LeagueTutorial.tutorial_id == Tutorial.id
        ).where(LeagueTutorial.league_id == league_id)
    tutorials = session.exec(query).all()
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
                "exercise_hints": exercise.exercise_hints,
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


# ---------------------------------------------------------------------------
# Admin CRUD. Students never see entry_function/test_code; the admin detail
# view below is the only read path that returns them.
# ---------------------------------------------------------------------------


def _get_tutorial_or_raise(session: Session, tutorial_id: int) -> Tutorial:
    tutorial = session.get(Tutorial, tutorial_id)
    if not tutorial:
        raise TutorialNotFoundError(f"Tutorial with ID {tutorial_id} not found")
    return tutorial


def _exercise_admin_dict(exercise: Exercise) -> dict:
    return {
        "id": exercise.id,
        "tutorial_id": exercise.tutorial_id,
        "order_index": exercise.order_index,
        "title": exercise.title,
        "problem_markdown": exercise.problem_markdown,
        "starter_code": exercise.starter_code,
        "entry_function": exercise.entry_function,
        "test_code": exercise.test_code,
        "solution": exercise.solution,
        "exercise_hints": exercise.exercise_hints,
    }


def _raise_if_title_taken(
    session: Session, title: str, exclude_id: Optional[int] = None
) -> None:
    query = select(Tutorial).where(Tutorial.title == title)
    if exclude_id is not None:
        query = query.where(Tutorial.id != exclude_id)
    if session.exec(query).first():
        raise TutorialExistsError(f"A tutorial titled '{title}' already exists")


def _delete_submission_history(session: Session, exercise_ids: list) -> None:
    """Delete all submission rows for the given exercises (metadata has an FK
    to exercise, so it must go before the exercises themselves)."""
    if not exercise_ids:
        return
    metadata_ids = session.exec(
        select(ExerciseSubmissionMetadata.id).where(
            ExerciseSubmissionMetadata.exercise_id.in_(exercise_ids)
        )
    ).all()
    if not metadata_ids:
        return
    for submission in session.exec(
        select(ExerciseSubmission).where(
            ExerciseSubmission.metadata_id.in_(metadata_ids)
        )
    ).all():
        session.delete(submission)
    for meta in session.exec(
        select(ExerciseSubmissionMetadata).where(
            ExerciseSubmissionMetadata.id.in_(metadata_ids)
        )
    ).all():
        session.delete(meta)


def get_tutorial_admin_detail(session: Session, tutorial_id: int) -> dict:
    """One tutorial with full exercise definitions (admin only)."""
    tutorial = _get_tutorial_or_raise(session, tutorial_id)
    return {
        "id": tutorial.id,
        "title": tutorial.title,
        "description": tutorial.description,
        "exercises": [
            _exercise_admin_dict(exercise) for exercise in tutorial.exercises
        ],
    }


def create_tutorial(session: Session, title: str, description: str) -> dict:
    _raise_if_title_taken(session, title)
    tutorial = Tutorial(title=title, description=description)
    session.add(tutorial)
    session.commit()
    session.refresh(tutorial)
    return {
        "id": tutorial.id,
        "title": tutorial.title,
        "description": tutorial.description,
    }


def update_tutorial(
    session: Session, tutorial_id: int, title: str, description: str
) -> dict:
    tutorial = _get_tutorial_or_raise(session, tutorial_id)
    _raise_if_title_taken(session, title, exclude_id=tutorial_id)
    tutorial.title = title
    tutorial.description = description
    session.commit()
    return {
        "id": tutorial.id,
        "title": tutorial.title,
        "description": tutorial.description,
    }


def delete_tutorial(session: Session, tutorial_id: int) -> None:
    """Delete a tutorial, its exercises, all their submission history, and
    its league attachments."""
    tutorial = _get_tutorial_or_raise(session, tutorial_id)
    _delete_submission_history(
        session, [exercise.id for exercise in tutorial.exercises]
    )
    for link in session.exec(
        select(LeagueTutorial).where(LeagueTutorial.tutorial_id == tutorial_id)
    ).all():
        session.delete(link)
    # The exercises relationship cascades with delete-orphan.
    session.delete(tutorial)
    session.commit()


def get_league_tutorial_ids(session: Session, league_id: int) -> list:
    """Ids of the tutorials attached to a league, in tutorial-id order."""
    return list(
        session.exec(
            select(LeagueTutorial.tutorial_id)
            .where(LeagueTutorial.league_id == league_id)
            .order_by(LeagueTutorial.tutorial_id)
        ).all()
    )


def validate_tutorial_ids(session: Session, tutorial_ids: list) -> None:
    """Raise TutorialNotFoundError (404) unless every id exists."""
    wanted = set(tutorial_ids)
    if not wanted:
        return
    found = set(
        session.exec(select(Tutorial.id).where(Tutorial.id.in_(wanted))).all()
    )
    missing = wanted - found
    if missing:
        raise TutorialNotFoundError(
            f"Tutorial with ID {sorted(missing)[0]} not found"
        )


def set_league_tutorials(
    session: Session, league_id: int, tutorial_ids: list, commit: bool = True
) -> list:
    """Replace a league's attached tutorials with exactly `tutorial_ids`.

    Replace-all semantics (like reorder_exercises) so the caller never has to
    reason about attach/detach deltas. Unknown tutorial ids 404 before
    anything is changed. Returns the new id list.
    """
    validate_tutorial_ids(session, tutorial_ids)
    wanted = set(tutorial_ids)

    existing = {
        link.tutorial_id: link
        for link in session.exec(
            select(LeagueTutorial).where(LeagueTutorial.league_id == league_id)
        ).all()
    }
    for tutorial_id, link in existing.items():
        if tutorial_id not in wanted:
            session.delete(link)
    for tutorial_id in wanted - set(existing):
        session.add(
            LeagueTutorial(league_id=league_id, tutorial_id=tutorial_id)
        )
    if commit:
        session.commit()
    return sorted(wanted)


def create_exercise(
    session: Session,
    tutorial_id: int,
    title: str,
    problem_markdown: str,
    starter_code: str,
    entry_function: str,
    test_code: Optional[str],
    solution: Optional[str],
    exercise_hints: list,
) -> dict:
    """Append a new exercise at the end of the tutorial.

    An exercise created without a test script (test_code=None) errors with
    "This exercise defines no tests" on submission until one is saved.
    """
    tutorial = _get_tutorial_or_raise(session, tutorial_id)
    next_index = max(
        (exercise.order_index for exercise in tutorial.exercises), default=-1
    ) + 1
    exercise = Exercise(
        tutorial_id=tutorial_id,
        order_index=next_index,
        title=title,
        problem_markdown=problem_markdown,
        starter_code=starter_code,
        entry_function=entry_function,
        test_code=test_code,
        solution=solution,
        exercise_hints=exercise_hints,
    )
    session.add(exercise)
    session.commit()
    session.refresh(exercise)
    return _exercise_admin_dict(exercise)


def update_exercise(
    session: Session,
    exercise_id: int,
    title: str,
    problem_markdown: str,
    starter_code: str,
    entry_function: str,
    test_code: Optional[str],
    solution: Optional[str],
    exercise_hints: list,
) -> dict:
    exercise = get_exercise_by_id(session, exercise_id)
    exercise.title = title
    exercise.problem_markdown = problem_markdown
    exercise.starter_code = starter_code
    exercise.entry_function = entry_function
    exercise.test_code = test_code
    exercise.solution = solution
    exercise.exercise_hints = exercise_hints
    session.commit()
    session.refresh(exercise)
    return _exercise_admin_dict(exercise)


def delete_exercise(session: Session, exercise_id: int) -> None:
    """Delete one exercise and its submission history, then close the gap in
    the remaining exercises' order_index values."""
    exercise = get_exercise_by_id(session, exercise_id)
    tutorial_id = exercise.tutorial_id
    _delete_submission_history(session, [exercise.id])
    session.delete(exercise)
    session.flush()

    remaining = session.exec(
        select(Exercise)
        .where(Exercise.tutorial_id == tutorial_id)
        .order_by(Exercise.order_index)
    ).all()
    for index, sibling in enumerate(remaining):
        sibling.order_index = index
    session.commit()


def reorder_exercises(
    session: Session, tutorial_id: int, exercise_ids: list
) -> dict:
    """Apply a complete new ordering. `exercise_ids` must be exactly the
    tutorial's exercise ids, each appearing once."""
    tutorial = _get_tutorial_or_raise(session, tutorial_id)
    current_ids = {exercise.id for exercise in tutorial.exercises}
    if len(exercise_ids) != len(set(exercise_ids)) or set(
        exercise_ids
    ) != current_ids:
        raise ExerciseReorderError(
            "Reorder list must contain each of the tutorial's exercise ids "
            "exactly once"
        )
    by_id = {exercise.id: exercise for exercise in tutorial.exercises}
    for index, exercise_id in enumerate(exercise_ids):
        by_id[exercise_id].order_index = index
    session.commit()
    session.refresh(tutorial)
    return get_tutorial_admin_detail(session, tutorial_id)


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
