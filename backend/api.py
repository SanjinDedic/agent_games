import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.models_api import ResponseModel
from backend.routes.auth.auth_db import InvalidCredentialsError
from backend.routes.admin.admin_db import (
    AgentTeamError,
    InstitutionExistsError,
    InstitutionNotFoundError,
)
from backend.routes.support.support_db import SupportError
from backend.routes.admin.admin_router import admin_router
from backend.routes.agent.agent_router import agent_router
from backend.routes.ai.ai_router import ai_router
from backend.routes.auth.auth_router import auth_router
from backend.routes.demo.demo_router import demo_router
from backend.routes.diagnostics.diagnostics_router import diagnostics_router
from backend.routes.institution.institution_router import institution_router
from backend.routes.payments.payments_router import payments_router
from backend.routes.support.support_router import support_router
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


@app.get("/", response_model=ResponseModel)
async def root():
    """Root endpoint to check if server is running"""
    return ResponseModel(status="success", message="Server is up and running")


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {"status": "healthy"}
