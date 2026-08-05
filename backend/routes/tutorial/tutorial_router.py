from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session

from backend.database.code_env import (
    ENV_LAMBDA,
    ENV_PYODIDE,
    KIND_EXERCISE,
    record_code_env_call,
)
from backend.database.db_session import get_db
from backend.routes.auth.auth_core import (
    get_current_user,
    verify_admin_role,
    verify_ai_agent_service_or_student,
    verify_any_role,
)
from backend.routes.tutorial.tutorial_db import (
    allow_exercise_submission,
    assert_exercise_in_team_league,
    assert_tutorial_in_team_league,
    create_exercise,
    create_tutorial,
    delete_exercise,
    delete_tutorial,
    get_exercise_by_id,
    get_exercise_submission_history,
    get_latest_exercise_submission,
    get_team_league_id,
    get_tutorial_admin_detail,
    get_tutorial_progress,
    get_tutorial_with_exercises,
    get_tutorials,
    record_failed_exercise_submission,
    record_hint_reveal,
    reorder_exercises,
    save_exercise_submission,
    update_exercise,
    update_tutorial,
)
from backend.routes.tutorial.pyodide_support import (
    normalize_client_rows,
    record_pyodide_fallback,
)
from backend.routes.tutorial.tutorial_models import (
    ExerciseReorderRequest,
    ExerciseRequest,
    ExerciseResultSubmissionRequest,
    HintRevealRequest,
    TutorialCreateRequest,
    TutorialUpdateRequest,
)

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


@tutorial_router.post("/submit-exercise-result")
@verify_ai_agent_service_or_student
async def submit_exercise_result(
    submission: ExerciseResultSubmissionRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Persist an exercise attempt the browser already ran via Pyodide.

    The in-browser runner (frontend/src/pyodide/exercise_harness.py, kept in
    lockstep with the server executor by test_exercise_harness_parity.py) runs
    the code and test script locally, then reports the finished envelope here
    so progress tracking and submission history stay identical to worker-run
    attempts. Client results are trusted by design — exercises are practice,
    not assessment — but each row is rebuilt from its contract keys, `passed`
    is recomputed server-side, and every stored row is stamped
    "source": "pyodide".

    This is the only submission path: the server never executes exercise
    code. Auth, league check, and a 5/minute budget guard it; the response
    contract is 400 with detail+stdout when the run produced no test results.

    execution_source="pyodide_fallback" marks an envelope the browser got by
    calling the fallback Lambda's Function URL directly (no API in the
    execution leg): the submission then doubles as the fallback-telemetry
    beacon and the stored rows are stamped "lambda_direct".
    """
    team_id = _require_team_id(current_user)
    exercise = get_exercise_by_id(session, submission.exercise_id)
    assert_exercise_in_team_league(session, exercise, team_id)
    allow_exercise_submission(session, team_id)

    direct_lambda = submission.execution_source == "pyodide_fallback"
    if direct_lambda:
        # Counted after the rate limit so spam can't inflate the telemetry.
        record_pyodide_fallback(
            team_id, submission.fallback_reason or "unspecified"
        )
    # Post-rate-limit so spam can't inflate the counter: this endpoint
    # persists runs the browser executed via Pyodide or fetched from the
    # direct Lambda.
    record_code_env_call(
        session,
        current_user["team_name"],
        KIND_EXERCISE,
        ENV_LAMBDA if direct_lambda else ENV_PYODIDE,
    )

    test_results = normalize_client_rows(
        submission.test_results, "lambda_direct" if direct_lambda else "pyodide"
    )

    if submission.status == "error" or not test_results:
        record_failed_exercise_submission(
            session, team_id, exercise.id, duration_ms=submission.duration_ms
        )
        return JSONResponse(
            status_code=400,
            content={
                "detail": submission.message or "Exercise run failed",
                "stdout": submission.stdout,
            },
        )

    passed = all(row["passed"] for row in test_results)
    submission_id = save_exercise_submission(
        session,
        submission.code,
        team_id,
        exercise.id,
        passed=passed,
        test_results=test_results,
        duration_ms=submission.duration_ms,
    )
    return {
        "submission_id": submission_id,
        "exercise_id": exercise.id,
        "passed": passed,
        "test_results": test_results,
        "stdout": submission.stdout,
        "duration_ms": submission.duration_ms,
    }


def _is_content_manager(current_user: dict) -> bool:
    """Admins and institutions browse the full tutorial library (they attach
    tutorials to leagues); every other role sees only its league's tutorials."""
    return current_user.get("role") in ("admin", "institution")


@tutorial_router.get("/tutorials")
@verify_any_role
async def get_tutorials_endpoint(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """List tutorials with their exercise counts.

    Admin/institution tokens see the full library; team tokens see only the
    tutorials attached to their league.
    """
    if _is_content_manager(current_user):
        return get_tutorials(session)

    team_id = current_user.get("team_id")
    league_id = (
        get_team_league_id(session, team_id) if team_id is not None else None
    )
    if league_id is None:
        return {"tutorials": []}
    return get_tutorials(session, league_id=league_id)


@tutorial_router.get("/tutorial/{tutorial_id}")
@verify_any_role
async def get_tutorial_endpoint(
    tutorial_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get one tutorial with its exercises in order.

    Team tokens can only open tutorials attached to their league; anything
    else 404s exactly like a nonexistent id.
    """
    if not _is_content_manager(current_user):
        team_id = _require_team_id(current_user)
        assert_tutorial_in_team_league(session, tutorial_id, team_id)
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
    assert_tutorial_in_team_league(session, tutorial_id, team_id)
    return get_tutorial_progress(session, team_id, tutorial_id)


# ---------------------------------------------------------------------------
# Admin content management. The admin detail endpoint is the only read path
# exposing `solution`; entry_function/test_code also ship in the student
# tutorial payload so the browser can run exercises via Pyodide.
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
        test_code=exercise.test_code,
        solution=exercise.solution,
        exercise_hints=exercise.exercise_hints,
    )


@tutorial_router.put("/exercise/{exercise_id}")
@verify_admin_role
async def update_exercise_endpoint(
    exercise_id: int,
    exercise: ExerciseRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Replace an exercise's definition (all fields, tests included)."""
    return update_exercise(
        session,
        exercise_id,
        title=exercise.title,
        problem_markdown=exercise.problem_markdown,
        starter_code=exercise.starter_code,
        entry_function=exercise.entry_function,
        test_code=exercise.test_code,
        solution=exercise.solution,
        exercise_hints=exercise.exercise_hints,
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
    exercise = get_exercise_by_id(session, exercise_id)
    assert_exercise_in_team_league(session, exercise, team_id)
    return get_latest_exercise_submission(session, team_id, exercise_id)


@tutorial_router.post("/exercise/{exercise_id}/hint-revealed")
@verify_ai_agent_service_or_student
async def record_hint_reveal_endpoint(
    exercise_id: int,
    reveal: HintRevealRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Record that the current team revealed one hint of an exercise.

    Feeds the concept mastery metric, which counts a revealed hint as extra
    effort. Repeat reveals of the same hint are a no-op, so the client can
    fire this unconditionally.
    """
    team_id = _require_team_id(current_user)
    exercise = get_exercise_by_id(session, exercise_id)
    assert_exercise_in_team_league(session, exercise, team_id)
    record_hint_reveal(session, team_id, exercise_id, reveal.hint_index)
    return {"status": "success"}


@tutorial_router.get("/exercise/{exercise_id}/submissions")
@verify_ai_agent_service_or_student
async def get_exercise_submissions_endpoint(
    exercise_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Full submission history by the current team for one exercise."""
    team_id = _require_team_id(current_user)
    exercise = get_exercise_by_id(session, exercise_id)
    assert_exercise_in_team_league(session, exercise, team_id)
    return {
        "submissions": get_exercise_submission_history(
            session, team_id, exercise_id
        )
    }
