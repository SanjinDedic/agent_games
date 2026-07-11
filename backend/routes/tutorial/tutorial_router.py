import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session

from backend.database.db_session import get_db
from backend.routes.auth.auth_core import (
    get_current_user,
    verify_admin_role,
    verify_ai_agent_service_or_student,
    verify_any_role,
)
from backend.routes.tutorial.tutorial_db import (
    allow_exercise_submission,
    create_exercise,
    create_tutorial,
    delete_exercise,
    delete_tutorial,
    get_exercise_by_id,
    get_exercise_submission_history,
    get_latest_exercise_submission,
    get_tutorial_admin_detail,
    get_tutorial_progress,
    get_tutorial_with_exercises,
    get_tutorials,
    record_failed_exercise_submission,
    reorder_exercises,
    save_exercise_submission,
    update_exercise,
    update_tutorial,
)
from backend.routes.tutorial.tutorial_models import (
    ExerciseRequest,
    ExerciseReorderRequest,
    ExerciseSubmissionRequest,
    TutorialCreateRequest,
    TutorialUpdateRequest,
)
from backend.routes.user.code_validation import validate_code
from backend.tasks.exercise_task import (
    await_exercise_result,
    enqueue_exercise_run,
)

logger = logging.getLogger(__name__)

tutorial_router = APIRouter()

# Same convention as user_router: business failures surface via the HTTP
# status line. tutorial_db's TutorialNotFoundError / ExerciseNotFoundError map
# to 404 in api.py; the reused SubmissionLimitExceededError maps to 429.


def _require_team_id(current_user: dict) -> int:
    """Reject tokens that don't carry a team_id (admin/institution tokens)."""
    team_id = current_user.get("team_id")
    if team_id is None:
        raise HTTPException(
            status_code=400, detail="This endpoint requires a team token"
        )
    return team_id


@tutorial_router.post("/submit-exercise")
@verify_ai_agent_service_or_student
async def submit_exercise(
    submission: ExerciseSubmissionRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Submit exercise code, run its test cases, and store the attempt.

    Failing test cases are a normal outcome — the response is a 200 whose
    test_results say which cases passed. HTTP 400 means the code never
    produced test results at all (unsafe code, a syntax error, a missing
    entry function, or a timeout); those attempts are recorded without code,
    mirroring failed agent validation.
    """
    team_id = _require_team_id(current_user)
    exercise = get_exercise_by_id(session, submission.exercise_id)
    allow_exercise_submission(session, team_id)

    # AST safety check runs here, before enqueue: cheap, and unsafe code
    # never reaches a worker.
    is_safe, error_message = validate_code(submission.code)
    if not is_safe:
        run_result = {
            "status": "error",
            "message": f"Code is not safe: {error_message}",
            "duration_ms": None,
        }
    else:
        logger.info(
            f"Enqueueing exercise run for team {team_id}, "
            f"exercise {exercise.id}"
        )
        async_result = enqueue_exercise_run(
            code=submission.code,
            entry_function=exercise.entry_function,
            test_cases=exercise.test_cases,
        )
        run_result = await await_exercise_result(async_result)

    duration_ms = run_result.get("duration_ms")

    if run_result.get("status") == "error":
        record_failed_exercise_submission(
            session, team_id, exercise.id, duration_ms=duration_ms
        )
        return JSONResponse(
            status_code=400,
            content={
                "detail": run_result.get("message", "Exercise run failed"),
                "stdout": run_result.get("stdout"),
            },
        )

    passed = run_result.get("passed", False)
    test_results = run_result.get("test_results", [])
    submission_id = save_exercise_submission(
        session,
        submission.code,
        team_id,
        exercise.id,
        passed=passed,
        test_results=test_results,
        duration_ms=duration_ms,
    )
    return {
        "submission_id": submission_id,
        "exercise_id": exercise.id,
        "passed": passed,
        "test_results": test_results,
        "stdout": run_result.get("stdout"),
        "duration_ms": duration_ms,
    }


@tutorial_router.get("/tutorials")
@verify_any_role
async def get_tutorials_endpoint(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """List all tutorials with their exercise counts."""
    return get_tutorials(session)


@tutorial_router.get("/tutorial/{tutorial_id}")
@verify_any_role
async def get_tutorial_endpoint(
    tutorial_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get one tutorial with its exercises in order."""
    return get_tutorial_with_exercises(session, tutorial_id)


@tutorial_router.get("/tutorial/{tutorial_id}/progress")
@verify_ai_agent_service_or_student
async def get_tutorial_progress_endpoint(
    tutorial_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Current team's attempted/passed status for each exercise, in order."""
    team_id = _require_team_id(current_user)
    return get_tutorial_progress(session, team_id, tutorial_id)


# ---------------------------------------------------------------------------
# Admin content management. The admin detail endpoint is the only read path
# exposing entry_function/test_cases — the student endpoints above keep them
# server-side.
# ---------------------------------------------------------------------------


@tutorial_router.get("/admin/tutorial/{tutorial_id}")
@verify_admin_role
async def get_tutorial_admin_endpoint(
    tutorial_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """One tutorial with full exercise definitions, including test cases."""
    return get_tutorial_admin_detail(session, tutorial_id)


@tutorial_router.post("/tutorials")
@verify_admin_role
async def create_tutorial_endpoint(
    tutorial: TutorialCreateRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create an empty tutorial."""
    return create_tutorial(session, tutorial.title, tutorial.description)


@tutorial_router.put("/tutorial/{tutorial_id}")
@verify_admin_role
async def update_tutorial_endpoint(
    tutorial_id: int,
    tutorial: TutorialUpdateRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Update a tutorial's title and description."""
    return update_tutorial(
        session, tutorial_id, tutorial.title, tutorial.description
    )


@tutorial_router.delete("/tutorial/{tutorial_id}")
@verify_admin_role
async def delete_tutorial_endpoint(
    tutorial_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Delete a tutorial, its exercises, and their submission history."""
    delete_tutorial(session, tutorial_id)
    return {"detail": "Tutorial deleted"}


@tutorial_router.post("/tutorial/{tutorial_id}/exercises")
@verify_admin_role
async def create_exercise_endpoint(
    tutorial_id: int,
    exercise: ExerciseRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Append a new exercise at the end of the tutorial."""
    return create_exercise(
        session,
        tutorial_id,
        title=exercise.title,
        problem_markdown=exercise.problem_markdown,
        starter_code=exercise.starter_code,
        entry_function=exercise.entry_function,
        test_cases=[case.model_dump() for case in exercise.test_cases],
    )


@tutorial_router.put("/exercise/{exercise_id}")
@verify_admin_role
async def update_exercise_endpoint(
    exercise_id: int,
    exercise: ExerciseRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Replace an exercise's definition (all fields)."""
    return update_exercise(
        session,
        exercise_id,
        title=exercise.title,
        problem_markdown=exercise.problem_markdown,
        starter_code=exercise.starter_code,
        entry_function=exercise.entry_function,
        test_cases=[case.model_dump() for case in exercise.test_cases],
    )


@tutorial_router.delete("/exercise/{exercise_id}")
@verify_admin_role
async def delete_exercise_endpoint(
    exercise_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Delete one exercise and its submission history."""
    delete_exercise(session, exercise_id)
    return {"detail": "Exercise deleted"}


@tutorial_router.post("/tutorial/{tutorial_id}/exercises/reorder")
@verify_admin_role
async def reorder_exercises_endpoint(
    tutorial_id: int,
    reorder: ExerciseReorderRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Apply a complete new exercise ordering for a tutorial."""
    return reorder_exercises(session, tutorial_id, reorder.exercise_ids)


@tutorial_router.get("/exercise/{exercise_id}/latest-submission")
@verify_ai_agent_service_or_student
async def get_latest_exercise_submission_endpoint(
    exercise_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Latest stored submission by the current team for one exercise."""
    team_id = _require_team_id(current_user)
    get_exercise_by_id(session, exercise_id)
    return get_latest_exercise_submission(session, team_id, exercise_id)


@tutorial_router.get("/exercise/{exercise_id}/submissions")
@verify_ai_agent_service_or_student
async def get_exercise_submissions_endpoint(
    exercise_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Full submission history by the current team for one exercise."""
    team_id = _require_team_id(current_user)
    get_exercise_by_id(session, exercise_id)
    return {
        "submissions": get_exercise_submission_history(
            session, team_id, exercise_id
        )
    }
