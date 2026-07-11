import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.models_api import ResponseModel
from backend.routes.agent.agent_db import SimulationLimitExceededError
from backend.routes.auth.auth_db import InvalidCredentialsError
from backend.routes.admin.admin_db import (
    AgentTeamError,
    InstitutionExistsError,
    InstitutionNotFoundError,
)
from backend.routes.support.support_db import SupportError
from backend.routes.ai.clients import (
    AIRequestTimeoutError,
    LLMResponseError,
    NoApiKeyError,
    UnknownProviderError,
)
from backend.routes.ai.plagiarism_service import (
    NoSubmissionsError,
    PayloadTooLargeError,
)
from backend.routes.institution.institution_db import (
    InstitutionAccessError,
    LeagueExistsError,
    LeagueNotFoundError,
    ProtectedLeagueError,
    SchoolsConfigError,
    SimulationResultNotFoundError,
    TeamExistsError,
    TeamNotFoundError,
)
from backend.routes.payments.payments_db import (
    InstitutionExistsError as PaidInstitutionExistsError,
    PaidSignupError,
)
from backend.routes.tutorial.tutorial_db import (
    ExerciseNotFoundError,
    ExerciseReorderError,
    TutorialExistsError,
    TutorialNotFoundError,
)
from backend.routes.user.user_db import (
    DemoLeagueError,
    LeagueExpiredError,
    ResultNotFoundError,
    SubmissionLimitExceededError,
    LeagueNotFoundError as UserLeagueNotFoundError,
    TeamExistsError as UserTeamExistsError,
    TeamNotFoundError as UserTeamNotFoundError,
)
from backend.routes.admin.admin_router import admin_router
from backend.routes.agent.agent_router import agent_router
from backend.routes.ai.ai_router import ai_router
from backend.routes.auth.auth_router import auth_router
from backend.routes.demo.demo_router import demo_router
from backend.routes.diagnostics.diagnostics_router import diagnostics_router
from backend.routes.institution.institution_router import institution_router
from backend.routes.payments.payments_router import payments_router
from backend.routes.support.support_router import support_router
from backend.routes.tutorial.tutorial_router import tutorial_router
from backend.routes.user.user_router import user_router
from sqlmodel import Session, text

from backend.database.db_session import get_db_engine

logger = logging.getLogger(__name__)


def check_database_status():
    """Read-only boot check: log whether the database looks initialized.

    Must never run DDL or seed data — the lifespan executes in every gunicorn
    worker process, so init here races across workers. Schema init/seed is a
    one-shot pre-start step (python -m backend.database.init_db) run by the
    container command before the server starts.
    """
    if os.environ.get("DB_ENVIRONMENT") == "test":
        # The test suite owns the test schema (conftest drops, creates and
        # truncates it at will); a boot-time read can hit a half-built schema
        # and log misleading warnings.
        logger.warning("DB_ENVIRONMENT=test — skipping database check")
        return
    try:
        engine = get_db_engine()
        with Session(engine) as session:
            # Check if admin table exists and has data
            admin_count = session.exec(text("SELECT COUNT(*) FROM admin")).first()
        if admin_count[0] == 0:
            logger.warning("=" * 60)
            logger.warning("🚨 DATABASE APPEARS EMPTY")
            logger.warning("No admin users found.")
            logger.warning("Run manually: python -m backend.database.init_db")
            logger.warning("=" * 60)
        else:
            logger.warning("=" * 60)
            logger.warning("✅ DATABASE PROPERLY INITIALIZED")
            logger.warning(f"Found {admin_count[0]} admin user(s) in database.")
            logger.warning("=" * 60)
    except Exception as e:
        logger.warning("=" * 60)
        logger.warning("🚨 DATABASE CHECK FAILED")
        logger.warning(f"Error: {e}")
        logger.warning("Database tables may not exist.")
        logger.warning("Run manually: python -m backend.database.init_db")
        logger.warning("=" * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application"""
    try:
        logger.info("Starting application...")
        check_database_status()
        # Container management now handled by Docker Compose

    except Exception as e:
        logger.error(f"Failed to start application: {e}")

    yield

    try:
        logger.info("Shutting down application...")
        # Container shutdown now handled by Docker Compose

    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")

app = FastAPI(lifespan=lifespan)


@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError):
    """Map failed authentication to HTTP 401 with a consistent {"detail": ...} body."""
    return JSONResponse(status_code=401, content={"detail": str(exc)})


# Domain exceptions -> HTTP status codes, applied wherever they propagate uncaught.
# Each maps to a consistent {"detail": ...} body (FastAPI's own convention).
@app.exception_handler(InstitutionNotFoundError)
async def institution_not_found_handler(request: Request, exc: InstitutionNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InstitutionExistsError)
async def institution_exists_handler(request: Request, exc: InstitutionExistsError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(AgentTeamError)
async def agent_team_error_handler(request: Request, exc: AgentTeamError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(SupportError)
async def support_error_handler(request: Request, exc: SupportError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


# AI / plagiarism + league-access domain exceptions -> HTTP status codes.
@app.exception_handler(LeagueNotFoundError)
async def league_not_found_handler(request: Request, exc: LeagueNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InstitutionAccessError)
async def institution_access_handler(request: Request, exc: InstitutionAccessError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(SimulationResultNotFoundError)
async def simulation_result_not_found_handler(
    request: Request, exc: SimulationResultNotFoundError
):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(LeagueExistsError)
async def league_exists_handler(request: Request, exc: LeagueExistsError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ProtectedLeagueError)
async def protected_league_handler(request: Request, exc: ProtectedLeagueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(SchoolsConfigError)
async def schools_config_handler(request: Request, exc: SchoolsConfigError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# TeamNotFoundError/TeamExistsError subclass TeamError; register the concrete
# subclasses so each maps to its own code (missing -> 404, duplicate -> 409).
@app.exception_handler(TeamNotFoundError)
async def team_not_found_handler(request: Request, exc: TeamNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(TeamExistsError)
async def team_exists_handler(request: Request, exc: TeamExistsError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(UnknownProviderError)
async def unknown_provider_handler(request: Request, exc: UnknownProviderError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(NoApiKeyError)
async def no_api_key_handler(request: Request, exc: NoApiKeyError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(NoSubmissionsError)
async def no_submissions_handler(request: Request, exc: NoSubmissionsError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(PayloadTooLargeError)
async def payload_too_large_handler(request: Request, exc: PayloadTooLargeError):
    return JSONResponse(status_code=413, content={"detail": str(exc)})


@app.exception_handler(LLMResponseError)
async def llm_response_error_handler(request: Request, exc: LLMResponseError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(AIRequestTimeoutError)
async def ai_timeout_handler(request: Request, exc: AIRequestTimeoutError):
    return JSONResponse(status_code=504, content={"detail": str(exc)})


@app.exception_handler(SimulationLimitExceededError)
async def simulation_limit_handler(request: Request, exc: SimulationLimitExceededError):
    return JSONResponse(status_code=429, content={"detail": str(exc)})


# User-domain exceptions (user_db defines its own league/team lookup errors,
# distinct classes from institution_db's; each maps to the same code).
@app.exception_handler(UserLeagueNotFoundError)
async def user_league_not_found_handler(request: Request, exc: UserLeagueNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(UserTeamNotFoundError)
async def user_team_not_found_handler(request: Request, exc: UserTeamNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(UserTeamExistsError)
async def user_team_exists_handler(request: Request, exc: UserTeamExistsError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ResultNotFoundError)
async def result_not_found_handler(request: Request, exc: ResultNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(LeagueExpiredError)
async def league_expired_handler(request: Request, exc: LeagueExpiredError):
    return JSONResponse(status_code=410, content={"detail": str(exc)})


@app.exception_handler(DemoLeagueError)
async def demo_league_handler(request: Request, exc: DemoLeagueError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(SubmissionLimitExceededError)
async def submission_limit_handler(request: Request, exc: SubmissionLimitExceededError):
    return JSONResponse(status_code=429, content={"detail": str(exc)})


# Tutorial-domain exceptions (exercise rate limiting reuses
# SubmissionLimitExceededError above).
@app.exception_handler(TutorialNotFoundError)
async def tutorial_not_found_handler(request: Request, exc: TutorialNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ExerciseNotFoundError)
async def exercise_not_found_handler(request: Request, exc: ExerciseNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(TutorialExistsError)
async def tutorial_exists_handler(request: Request, exc: TutorialExistsError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ExerciseReorderError)
async def exercise_reorder_handler(request: Request, exc: ExerciseReorderError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# Payments-domain exceptions: signup validation -> 400; the duplicate-name
# subclass -> 409 (matches the other "exists" mappings). Starlette resolves
# handlers by MRO, so the subclass handler wins over the base.
@app.exception_handler(PaidSignupError)
async def paid_signup_error_handler(request: Request, exc: PaidSignupError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(PaidInstitutionExistsError)
async def paid_institution_exists_handler(
    request: Request, exc: PaidInstitutionExistsError
):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(admin_router, prefix="/admin", tags=["Administration"])
app.include_router(institution_router, prefix="/institution", tags=["Institution"])
app.include_router(user_router, prefix="/user", tags=["User Operations"])
app.include_router(agent_router, prefix="/agent", tags=["Agent Operations"])
app.include_router(demo_router, prefix="/demo", tags=["Demo Operations"])
app.include_router(ai_router, prefix="/ai", tags=["AI Configuration"])
app.include_router(diagnostics_router, prefix="/diagnostics", tags=["Diagnostics"])
app.include_router(support_router, prefix="/support", tags=["Support"])
app.include_router(payments_router, prefix="/payments", tags=["Payments"])
app.include_router(tutorial_router, prefix="/tutorial", tags=["Tutorial"])


@app.get("/", response_model=ResponseModel)
async def root():
    """Root endpoint to check if server is running"""
    return ResponseModel(status="success", message="Server is up and running")


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {"status": "healthy"}
