import logging
from typing import Optional

import redis
from sqlmodel import Session, select

from backend.database.db_models import Lesson
# Reused so the existing 429 handler in api.py covers snippet rate limiting.
from backend.routes.user.user_db import SubmissionLimitExceededError
from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


class LessonNotFoundError(Exception):
    """Raised when a lesson is not found (maps to HTTP 404)."""

    pass


class LessonExistsError(Exception):
    """Raised when a lesson slug is already taken (maps to HTTP 409)."""

    pass


# Snippet runs create no DB rows (unlike exercise submissions, which are
# rate-limited by counting ExerciseSubmissionMetadata), so the budget is a
# fixed-window counter in Valkey — shared across the API's gunicorn workers,
# which an in-process counter would undercount.
SNIPPET_RUNS_PER_MINUTE = 10

_rate_limit_client: Optional[redis.Redis] = None


def _get_rate_limit_client() -> redis.Redis:
    global _rate_limit_client
    if _rate_limit_client is None:
        # The Celery broker is Valkey; reuse its URL rather than configuring
        # a second connection setting.
        _rate_limit_client = redis.Redis.from_url(celery_app.conf.broker_url)
    return _rate_limit_client


def allow_snippet_run(identity: str) -> bool:
    """Check the caller's snippet-run budget (fixed one-minute window).

    Fails open on a Valkey error: if the broker is down the enqueue right
    after this call will fail loudly anyway, so refusing here adds nothing.
    """
    key = f"lesson-snippet-rate:{identity}"
    try:
        client = _get_rate_limit_client()
        count = client.incr(key)
        if count == 1:
            client.expire(key, 60)
    except redis.RedisError:
        logger.warning("Snippet rate-limit check failed; allowing run")
        return True
    if count > SNIPPET_RUNS_PER_MINUTE:
        raise SubmissionLimitExceededError(
            f"You can only run code {SNIPPET_RUNS_PER_MINUTE} times per minute."
        )
    return True


def _lesson_dict(lesson: Lesson) -> dict:
    return {
        "id": lesson.id,
        "slug": lesson.slug,
        "title": lesson.title,
        "content": lesson.content,
    }


def _get_lesson_or_raise(session: Session, lesson_id: int) -> Lesson:
    lesson = session.get(Lesson, lesson_id)
    if not lesson:
        raise LessonNotFoundError(f"Lesson with ID {lesson_id} not found")
    return lesson


def _raise_if_slug_taken(
    session: Session, slug: str, exclude_id: Optional[int] = None
) -> None:
    query = select(Lesson).where(Lesson.slug == slug)
    if exclude_id is not None:
        query = query.where(Lesson.id != exclude_id)
    if session.exec(query).first():
        raise LessonExistsError(f"A lesson with slug '{slug}' already exists")


def get_lesson_by_slug(session: Session, slug: str) -> dict:
    lesson = session.exec(
        select(Lesson).where(Lesson.slug == slug)
    ).first()
    if not lesson:
        raise LessonNotFoundError(f"Lesson '{slug}' not found")
    return _lesson_dict(lesson)


def get_lessons(session: Session) -> dict:
    """List all lessons without their content (the editor loads content
    through the by-slug endpoint when a lesson is opened)."""
    lessons = session.exec(select(Lesson).order_by(Lesson.slug)).all()
    return {
        "lessons": [
            {
                "id": lesson.id,
                "slug": lesson.slug,
                "title": lesson.title,
                "created_at": lesson.created_at.isoformat(),
            }
            for lesson in lessons
        ]
    }


def create_lesson(
    session: Session, slug: str, title: str, content: str
) -> dict:
    _raise_if_slug_taken(session, slug)
    lesson = Lesson(slug=slug, title=title, content=content)
    session.add(lesson)
    session.commit()
    session.refresh(lesson)
    return _lesson_dict(lesson)


def update_lesson(
    session: Session, lesson_id: int, slug: str, title: str, content: str
) -> dict:
    lesson = _get_lesson_or_raise(session, lesson_id)
    _raise_if_slug_taken(session, slug, exclude_id=lesson_id)
    lesson.slug = slug
    lesson.title = title
    lesson.content = content
    session.commit()
    session.refresh(lesson)
    return _lesson_dict(lesson)


def delete_lesson(session: Session, lesson_id: int) -> None:
    lesson = _get_lesson_or_raise(session, lesson_id)
    session.delete(lesson)
    session.commit()
