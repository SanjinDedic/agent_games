import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.models_api import ResponseModel
from backend.routes.admin.admin_router import admin_router
from backend.routes.agent.agent_router import agent_router
from backend.routes.auth.auth_router import auth_router
from backend.routes.demo.demo_router import demo_router
from backend.routes.institution.institution_router import institution_router
from backend.routes.user.user_router import user_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application"""
    try:
        logger.info("Starting application...")
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


@app.get("/", response_model=ResponseModel)
async def root():
    """Root endpoint to check if server is running"""
    return ResponseModel(status="success", message="Server is up and running")


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {"status": "healthy"}
