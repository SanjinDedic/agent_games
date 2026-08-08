import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend import config
from backend.errors import EXCEPTION_STATUS_MAP
from backend.models_api import ResponseModel
from backend.routes.agent.agent_router import agent_router
from backend.routes.ai.ai_router import ai_router
from backend.routes.auth.auth_db import owner_exists
from backend.routes.auth.auth_router import auth_router
from backend.routes.diagnostics.diagnostics_router import diagnostics_router
from backend.routes.owner.owner_router import owner_router
from backend.routes.user.user_router import user_router
from sqlmodel import Session, text

from backend.database.db_session import get_db, get_db_engine

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
            owner_count = session.exec(text("SELECT COUNT(*) FROM owner")).first()
        if owner_count[0] == 0:
            logger.warning("=" * 60)
            logger.warning("📋 DEPLOYMENT NOT YET CLAIMED")
            logger.warning("No owner account — visit the frontend to set one up.")
            logger.warning("=" * 60)
        else:
            logger.warning("=" * 60)
            logger.warning("✅ DATABASE PROPERLY INITIALIZED")
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


# Domain exceptions -> HTTP status codes, applied wherever they propagate
# uncaught. Every mapping lives in backend/errors.py; this loop is the only
# place handlers are registered, and each returns FastAPI's own
# {"detail": ...} body shape.
#
# The factory closes over `status` per iteration — a handler that read `status`
# from the enclosing scope would see whatever the last iteration left behind
# and give every exception the same code.
def _make_domain_handler(status: int):
    async def handler(request: Request, exc: Exception):
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    return handler


for _exc_class, _status in EXCEPTION_STATUS_MAP.items():
    app.add_exception_handler(_exc_class, _make_domain_handler(_status))


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(owner_router, prefix="/owner", tags=["Owner"])
app.include_router(user_router, prefix="/user", tags=["User Operations"])
app.include_router(agent_router, prefix="/agent", tags=["Agent Operations"])
app.include_router(ai_router, prefix="/ai", tags=["AI Configuration"])
app.include_router(diagnostics_router, prefix="/diagnostics", tags=["Diagnostics"])


@app.get("/", response_model=ResponseModel)
async def root():
    """Root endpoint to check if server is running"""
    return ResponseModel(status="success", message="Server is up and running")


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {"status": "healthy"}


@app.get("/config")
async def site_config(session: Session = Depends(get_db)):
    """Deploy-level settings the frontend needs before anyone logs in.

    Unauthenticated and deliberately app-level rather than a router: this is
    metadata about the deployment, not a domain resource. `site_mode` drives the
    classroom-vs-competition wording the frontend renders, and `setup_required`
    tells it whether to offer the first-run setup form or the login form.
    """
    return {
        "site_mode": config.SITE_MODE,
        "site_name": config.SITE_NAME,
        "site_icon": config.SITE_ICON,
        "setup_required": not owner_exists(session),
    }
