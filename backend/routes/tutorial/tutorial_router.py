import logging

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
    verify_admin_or_institution,
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
    ExerciseRunRequest,
    ExerciseSubmissionRequest,
    HintRevealRequest,
    TutorialCreateRequest,
    TutorialUpdateRequest,
)
from backend.fallback_lambda.client import run_exercise_fallback

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
    produced test results at all (a syntax error, a missing entry function,
    or a timeout); those attempts are recorded without code, mirroring
    failed agent validation.

    Unlike agent submission there is no AST safety gate: the code goes
    straight to the sandboxed fallback runner (backend/fallback_lambda/),
    which is the enforcement boundary.
    """
    team_id = _require_team_id(current_user)
    exercise = get_exercise_by_id(session, submission.exercise_id)
    assert_exercise_in_team_league(session, exercise, team_id)
    allow_exercise_submission(session, team_id)

    if submission.execution_source == "pyodide_fallback":
        # The browser couldn't run this via Pyodide and fell back here;
        # counted after the rate limit so spam can't inflate the telemetry.
        record_pyodide_fallback(
            team_id, submission.fallback_reason or "unspecified"
        )

    # Environment counter (also post-rate-limit): everything through this
    # endpoint runs on the server path, fallback traffic included.
    record_code_env_call(
        session, current_user["team_name"], KIND_EXERCISE, ENV_LAMBDA
    )

    logger.info(
        f"Running exercise fallback for team {team_id}, "
        f"exercise {exercise.id}"
    )
    run_result = await run_exercise_fallback(
        code=submission.code,
        entry_function=exercise.entry_function,
        test_code=exercise.test_code,
    )

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
    if submission.execution_source == "pyodide_fallback":
        # Stamp the stored rows so fallback runs stay identifiable in the
        # submission history (the default server path stays untouched; the
        # stored "celery_fallback" value predates the Celery removal).
        test_results = normalize_client_rows(test_results, "celery_fallback")
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


@tutorial_router.post("/preview/submit-exercise")
@verify_admin_or_institution
async def preview_submit_exercise(
    submission: ExerciseSubmissionRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Run exercise code exactly like /submit-exercise but persist nothing.

    Backs the tutorial preview for institution/teacher/admin accounts: they
    try a tutorial as a fresh student would see it, so no submission or
    metadata rows may be written — every preview starts blank. Response shape
    mirrors /submit-exercise (submission_id is always null) so the same
    frontend workspace drives both. No league check (these roles browse the
    whole library) and no per-team rate limit (there is no team).
    """
    exercise = get_exercise_by_id(session, submission.exercise_id)

    if submission.execution_source == "pyodide_fallback":
        # Preview runs persist nothing, but a teacher's browser failing to
        # run Pyodide is the same signal as a student's — count it.
        record_pyodide_fallback(
            None, submission.fallback_reason or "unspecified"
        )

    run_result = await run_exercise_fallback(
        code=submission.code,
        entry_function=exercise.entry_function,
        test_code=exercise.test_code,
    )

    if run_result.get("status") == "error":
        return JSONResponse(
            status_code=400,
            content={
                "detail": run_result.get("message", "Exercise run failed"),
                "stdout": run_result.get("stdout"),
            },
        )

    return {
        "submission_id": None,
        "exercise_id": exercise.id,
        "passed": run_result.get("passed", False),
        "test_results": run_result.get("test_results", []),
        "stdout": run_result.get("stdout"),
        "duration_ms": run_result.get("duration_ms"),
    }


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

    Same auth, league check, and 5/minute budget as /submit-exercise, and the
    same response contract (400 with detail+stdout when the run produced no
    test results) so the frontend shares one result path.
    """
    team_id = _require_team_id(current_user)
    exercise = get_exercise_by_id(session, submission.exercise_id)
    assert_exercise_in_team_league(session, exercise, team_id)
    allow_exercise_submission(session, team_id)

    # Post-rate-limit like submit_exercise's counter: this endpoint only ever
    # persists runs the browser executed via Pyodide.
    record_code_env_call(
        session, current_user["team_name"], KIND_EXERCISE, ENV_PYODIDE
    )

    test_results = normalize_client_rows(submission.test_results, "pyodide")

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


@tutorial_router.post("/admin/run-exercise")
@verify_admin_role
async def run_exercise_endpoint(
    run: ExerciseRunRequest,
    current_user: dict = Depends(get_current_user),
):
    """Dry-run a test script against code without saving anything.

    Backs the admin exercise editor's Run button. Unlike /submit-exercise,
    every outcome is a 200 with the full run result — including `traceback`
    when the test script itself fails to exec, since the caller is the person
    debugging that script. Like student submissions, there is no AST safety
    gate — the sandboxed fallback runner is the enforcement boundary.
    """
    return await run_exercise_fallback(
        code=run.code,
        entry_function=run.entry_function,
        test_code=run.test_code,
    )


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
