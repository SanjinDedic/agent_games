import logging
import time

from fastapi import APIRouter, Depends, Header
from sqlmodel import Session

from backend.config import BENCHMARK_TOKEN
from backend.database.db_models import Institution
from backend.database.db_session import get_db
from backend.models_api import ErrorResponseModel, ResponseModel
from backend.routes.auth.auth_core import get_current_user, verify_admin_or_institution
from backend.routes.diagnostics.diagnostics_models import BenchmarkSubmission
from backend.routes.diagnostics.diagnostics_utils import get_all_services_status

from backend.routes.user.code_validation import (
    await_validation_result,
    enqueue_validation,
    validate_code,
)

logger = logging.getLogger(__name__)

diagnostics_router = APIRouter()


async def check_docker_access(current_user: dict, session: Session) -> bool:
    """Check if the current user has Docker access"""
    if current_user["role"] == "admin":
        return True

    if current_user["role"] == "institution":
        institution_id = current_user.get("institution_id")
        if not institution_id:
            return False

        institution = session.get(Institution, institution_id)
        if not institution or not institution.docker_access:
            return False

        return True

    return False


@diagnostics_router.get("/status", response_model=ResponseModel)
@verify_admin_or_institution
async def get_status(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get health status for the Celery broker and worker services"""
    has_access = await check_docker_access(current_user, session)
    if not has_access:
        return ErrorResponseModel(
            status="error",
            message="You don't have Docker access. Please contact the administrator.",
        )

    try:
        statuses = await get_all_services_status()
        return ResponseModel(
            status="success",
            message="Services status retrieved successfully",
            data={"statuses": statuses},
        )
    except Exception as e:
        logger.error(f"Error retrieving service status: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve service status: {str(e)}"
        )


@diagnostics_router.post("/benchmark-submit", response_model=ResponseModel)
async def benchmark_submit(
    submission: BenchmarkSubmission,
    x_benchmark_token: str = Header(default=""),
):
    """Load-test only. Runs the real validator submission path (the expensive
    part of /user/submit-agent) while skipping rate-limiting and DB logging, so
    a load tool can drive 100s of submissions/min without polluting the database
    or hitting the per-team submission cap.

    Gated by the BENCHMARK_TOKEN env var: when unset (the default, including
    prod) the endpoint is disabled and returns 403. There is no DB write and no
    auth/team lookup here on purpose — this isolates and measures validator
    throughput, which is what changes with code changes to the simulation path.
    """
    if not BENCHMARK_TOKEN:
        return ErrorResponseModel(
            status="error", message="Benchmark endpoint disabled."
        )
    if x_benchmark_token != BENCHMARK_TOKEN:
        return ErrorResponseModel(
            status="error", message="Invalid benchmark token."
        )

    t0 = time.perf_counter()
    try:
        is_safe, error_message = validate_code(submission.code)
        if not is_safe:
            result = {
                "status": "error",
                "message": f"Agent code is not safe: {error_message}",
                "duration_ms": None,
            }
        else:
            async_result = enqueue_validation(
                code=submission.code,
                game_name=submission.game_name,
                team_name="benchmark",
                num_simulations=submission.num_simulations,
            )
            result = await await_validation_result(async_result)
    except Exception as e:
        return ErrorResponseModel(
            status="error", message=f"Validator request failed: {str(e)}"
        )
    round_trip_ms = (time.perf_counter() - t0) * 1000

    return ResponseModel(
        status=result.get("status", "success"),
        message="benchmark ok",
        data={
            "validator_status": result.get("status"),
            "validator_duration_ms": result.get("duration_ms"),
            "round_trip_ms": round_trip_ms,
        },
    )
