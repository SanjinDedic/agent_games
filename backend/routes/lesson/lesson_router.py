from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.database.db_session import get_db
from backend.routes.auth.auth_core import (
    get_current_user,
    verify_admin_role,
    verify_any_role,
)
from backend.routes.lesson.lesson_db import (
    allow_snippet_run,
    create_lesson,
    delete_lesson,
    get_lesson_by_slug,
    get_lessons,
    update_lesson,
)
from backend.routes.lesson.lesson_models import (
    LessonRequest,
    SnippetFallbackBeacon,
)
from backend.routes.tutorial.pyodide_support import record_pyodide_fallback

lesson_router = APIRouter()

# Lessons are a global content library, not league-gated: they are reached
# through lesson://<slug> links embedded in content that is already gated
# (exercise problem markdown, tutorial descriptions), and contain no
# solutions or tests. lesson_db's LessonNotFoundError / LessonExistsError map
# to 404/409 in api.py; the reused SubmissionLimitExceededError maps to 429.


def _snippet_identity(current_user: dict) -> str:
    """Rate-limit key: per team for students, per institution or role
    otherwise, so an admin previewing a lesson never shares a budget with a
    class. (get_current_user carries no generic account id — team_id and
    institution_id are the only stable identifiers in the token.)"""
    team_id = current_user.get("team_id")
    if team_id is not None:
        return f"team:{team_id}"
    institution_id = current_user.get("institution_id")
    if institution_id is not None:
        return f"institution:{institution_id}"
    return str(current_user.get("role"))


@lesson_router.get("/lesson/{slug}")
@verify_any_role
async def get_lesson_endpoint(
    slug: str,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """One lesson by slug, content included."""
    return get_lesson_by_slug(session, slug)


@lesson_router.post("/snippet-fallback-beacon")
@verify_any_role
async def snippet_fallback_beacon_endpoint(
    beacon: SnippetFallbackBeacon,
    current_user: dict = Depends(get_current_user),
):
    """Count a snippet run the browser sent straight to the fallback Lambda.

    Fire-and-forget from the client after a direct Function URL call (there
    is no result to persist for snippets — this exists purely so the shared
    fallback telemetry keeps measuring when the folder can be deleted). The
    server never executes snippet code; the 10/min budget just bounds beacon
    spam so it can't inflate the counters.
    """
    allow_snippet_run(_snippet_identity(current_user))
    record_pyodide_fallback(
        current_user.get("team_id"),
        f"snippet:{beacon.reason or 'unspecified'}",
    )
    return {"detail": "recorded"}


# ---------------------------------------------------------------------------
# Admin content management.
# ---------------------------------------------------------------------------


@lesson_router.get("/lessons")
@verify_admin_role
async def get_lessons_endpoint(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """List all lessons (without content)."""
    return get_lessons(session)


@lesson_router.post("/lessons")
@verify_admin_role
async def create_lesson_endpoint(
    lesson: LessonRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a lesson."""
    return create_lesson(session, lesson.slug, lesson.title, lesson.content)


@lesson_router.put("/lesson/{lesson_id}")
@verify_admin_role
async def update_lesson_endpoint(
    lesson_id: int,
    lesson: LessonRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Replace a lesson's definition. Renaming the slug breaks any existing
    lesson:// links pointing at the old one — the editor warns about this."""
    return update_lesson(
        session, lesson_id, lesson.slug, lesson.title, lesson.content
    )


@lesson_router.delete("/lesson/{lesson_id}")
@verify_admin_role
async def delete_lesson_endpoint(
    lesson_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Delete a lesson. lesson:// links pointing at it will show the modal's
    not-found state."""
    delete_lesson(session, lesson_id)
    return {"detail": "Lesson deleted"}
