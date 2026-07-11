import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session

from backend.database.db_session import get_db
from backend.routes.auth.auth_core import (
    get_current_user,
    verify_ai_agent_service_or_student,
    verify_any_role,
)
from backend.routes.tutorial.tutorial_db import (
    allow_exercise_submission,
    get_exercise_by_id,
    get_exercise_submission_history,
    get_latest_exercise_submission,
    get_tutorial_with_exercises,
    get_tutorials,
    record_failed_exercise_submission,
    save_exercise_submission,
)
from backend.routes.tutorial.tutorial_models import ExerciseSubmissionRequest
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
