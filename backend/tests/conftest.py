import asyncio
import logging
import multiprocessing
import os
import shutil
import signal
import sys
from pathlib import Path

import pytest
import uvicorn
from fastapi.testclient import TestClient

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add project root to PYTHONPATH
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Import project modules after path setup
from api import app
from database import get_db_engine
from docker.containers import ensure_containers_running, stop_containers
from sqlmodel import Session


class UvicornTestServer(uvicorn.Server):
    """Custom Uvicorn test server with graceful shutdown support"""

    def __init__(self, app, host="127.0.0.1", port=8000):
        self._startup_done = asyncio.Event()
        super().__init__(
            config=uvicorn.Config(app, host=host, port=port, log_level="error")
        )

    async def startup(self, sockets=None):
        await super().startup(sockets)
        self._startup_done.set()

    async def shutdown(self, sockets=None):
        await super().shutdown(sockets)


def run_app():
    """Function to run the FastAPI application"""
    server = UvicornTestServer(app)
    server.run()


def create_test_directories():
    """Create and verify all necessary test directories"""
    root_dir = Path(__file__).parent.parent

    # Define required directory structure
    test_dirs = {
        "prisoners": {
            "test": root_dir
            / "games"
            / "prisoners_dilemma"
            / "leagues"
            / "test_league",
            "admin": root_dir / "games" / "prisoners_dilemma" / "leagues" / "admin",
        },
        "greedy": {
            "test": root_dir / "games" / "greedy_pig" / "leagues" / "test_league",
            "admin": root_dir / "games" / "greedy_pig" / "leagues" / "admin",
        },
    }

    # Create directories
    for game_dirs in test_dirs.values():
        for path in game_dirs.values():
            try:
                path.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    raise RuntimeError(f"Failed to create directory: {path}")
                logger.info(f"Verified directory exists: {path}")
            except Exception as e:
                logger.error(f"Error creating directory {path}: {str(e)}")
                raise

    return test_dirs


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Primary test environment setup fixture"""
    logger.info("Starting test environment setup")

    try:
        # Create test directories
        test_dirs = create_test_directories()

        # Start containers
        logger.info("Starting Docker containers")
        ensure_containers_running(project_root)

        # Start FastAPI in a separate process
        logger.info("Starting FastAPI server")
        proc = multiprocessing.Process(target=run_app)
        proc.start()

        # Allow server startup time
        import time

        time.sleep(5)
        logger.info("Test environment setup completed successfully")

        yield test_dirs

        # Cleanup
        logger.info("Starting test environment cleanup")
        os.kill(proc.pid, signal.SIGINT)
        proc.join(timeout=5)
        if proc.is_alive():
            proc.terminate()
            proc.join()

        stop_containers()
        logger.info("Test environment cleanup completed")

    except Exception as e:
        logger.error(f"Error in test environment setup/teardown: {str(e)}")
        raise


@pytest.fixture(scope="session")
def db_session():
    """Database session fixture"""
    logger.info("Creating database session")
    engine = get_db_engine()
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture(scope="session")
def client(db_session):
    """TestClient fixture"""
    logger.info("Creating test client")

    def get_db_session_override():
        return db_session

    app.dependency_overrides[get_db_engine] = get_db_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def temp_test_files(setup_test_environment):
    """Fixture for temporary test files"""
    logger.info("Setting up temporary test files")
    root_dir = Path(__file__).parent.parent

    # Create temporary test directory
    temp_dir = (
        root_dir / "games" / "prisoners_dilemma" / "leagues" / "dynamic_test_league"
    )
    temp_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created temporary directory: {temp_dir}")

    # Create test bot file
    test_bot_content = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 'collude'
"""
    test_bot_path = temp_dir / "test_bot.py"
    with open(test_bot_path, "w") as f:
        f.write(test_bot_content)
    logger.info(f"Created test bot at {test_bot_path}")

    yield {"dynamic": temp_dir}

    # Cleanup
    logger.info("Cleaning up temporary test files")
    shutil.rmtree(temp_dir)
