import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.models_api import ResponseModel
from backend.routes.admin.admin_router import admin_router
from backend.routes.agent.agent_router import agent_router
from backend.routes.auth.auth_router import auth_router
from backend.routes.demo.demo_router import demo_router
from backend.routes.diagnostics.diagnostics_router import diagnostics_router
from backend.routes.institution.institution_router import institution_router
from backend.routes.user.user_router import user_router
from sqlmodel import Session, create_engine, text

from backend.database.db_config import get_database_url

logger = logging.getLogger(__name__)


def check_database_status():
    """Check if database is initialized and warn if its not"""
    try:
        engine = create_engine(get_database_url())
        with Session(engine) as session:
            # Check if admin table exists and has data
            admin_count = session.exec(text("SELECT COUNT(*) FROM admin")).first()
            if admin_count[0] == 0:
                logger.warning("=" * 60)
                logger.warning("🚨 DATABASE APPEARS EMPTY")
                logger.warning("=" * 60)
                logger.warning(
                    "No admin users found. Database may need initialization."
                )
                logger.warning("Run: python backend/docker_utils/init_db.py")
                logger.warning("=" * 60)
            else:
                logger.warning("=" * 60)
                logger.warning("✅ DATABASE PROPERLY INITIALIZED")
                logger.warning("=" * 60)
                logger.warning(f"Found {admin_count[0]} admin user(s) in database.")
                logger.warning("=" * 60)
    except Exception as e:
        logger.warning("=" * 60)
        logger.warning("🚨 DATABASE CHECK FAILED")
        logger.warning("=" * 60)
        logger.warning(f"Error: {e}")
        logger.warning("Database may need initialization.")
        logger.warning("=" * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application"""
    try:
        logger.info("Starting application...")
        check_database_status()  # Add this line
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
app.include_router(diagnostics_router, prefix="/diagnostics", tags=["Diagnostics"])


@app.get("/", response_model=ResponseModel)
async def root():
    """Root endpoint to check if server is running"""
    return ResponseModel(status="success", message="Server is up and running")


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {"status": "healthy"}

