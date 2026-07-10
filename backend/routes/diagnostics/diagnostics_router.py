import time

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session

from backend.config import BENCHMARK_TOKEN
from backend.database.db_models import Institution
from backend.database.db_session import get_db
from backend.routes.auth.auth_core import get_current_user, verify_admin_or_institution
from backend.routes.diagnostics.diagnostics_models import BenchmarkSubmission
from backend.routes.diagnostics.diagnostics_utils import get_all_services_status

from backend.routes.user.code_validation import validate_code
from backend.tasks.validation_task import (
    await_validation_result,
    enqueue_validation,
)

diagnostics_router = APIRouter()

# Business failures surface via the HTTP status line: missing Docker access and a
# disabled / mis-tokened benchmark endpoint -> 403, raised here. An error while
# collecting service status or running the validator surfaces as a 500 rather than
# a masked 200. Each route returns its payload directly.


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


@diagnostics_router.get("/status")
@verify_admin_or_institution
async def get_status(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get health status for the Celery broker and worker services"""
    if not await check_docker_access(current_user, session):
        raise HTTPException(
            status_code=403,
            detail="You don't have Docker access. Please contact the administrator.",
        )

    return {"statuses": await get_all_services_status()}


@diagnostics_router.post("/benchmark-submit")
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
        raise HTTPException(status_code=403, detail="Benchmark endpoint disabled.")
    if x_benchmark_token != BENCHMARK_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid benchmark token.")

    t0 = time.perf_counter()
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
    round_trip_ms = (time.perf_counter() - t0) * 1000

    return {
        "validator_status": result.get("status"),
        "validator_duration_ms": result.get("duration_ms"),
        "round_trip_ms": round_trip_ms,
    }
