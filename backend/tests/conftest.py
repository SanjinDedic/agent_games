import asyncio
import logging
import multiprocessing
import os
import shutil
import signal
import sys
import warnings
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

# Suppress deprecation warnings during testing
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings(
        "ignore", category=UserWarning, message=".*error reading bcrypt version.*"
    )


def ensure_directory_structure():
    """
    Create and verify all necessary directories before any tests run.
    This is a standalone function that runs before any fixtures.
    """
    root_dir = Path(__file__).parent.parent

    # Define all required directories
    required_dirs = {
        # Protected directories (never deleted)
        "prisoners_test": root_dir
        / "games"
        / "prisoners_dilemma"
        / "leagues"
        / "test_league",
        "greedy_test": root_dir / "games" / "greedy_pig" / "leagues" / "test_league",
        "prisoners_admin": root_dir
        / "games"
        / "prisoners_dilemma"
        / "leagues"
        / "admin",
        "greedy_admin": root_dir / "games" / "greedy_pig" / "leagues" / "admin",
        # Game root directories
        "prisoners_root": root_dir / "games" / "prisoners_dilemma",
        "greedy_root": root_dir / "games" / "greedy_pig",
        # League directories
        "prisoners_leagues": root_dir / "games" / "prisoners_dilemma" / "leagues",
        "greedy_leagues": root_dir / "games" / "greedy_pig" / "leagues",
    }

    # Create directories and verify their existence
    for name, path in required_dirs.items():
        try:
            path.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                raise RuntimeError(f"Failed to create directory: {path}")
            logger.info(f"Verified directory exists: {name} at {path}")

            # Create .keep file in each directory
            keep_file = path / ".keep"
            keep_file.touch()
            logger.info(f"Created/verified .keep file in {name}")
        except Exception as e:
            logger.error(f"Error setting up directory {name}: {str(e)}")
            raise

    # Return the paths for use in fixtures
    return required_dirs


# Run directory setup immediately on module import
REQUIRED_DIRS = ensure_directory_structure()


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


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Primary test environment setup fixture.
    Assumes directories are already created by ensure_directory_structure()
    """
    logger.info("Starting test environment setup")

    try:
        # Start containers
        logger.info("Starting Docker containers")
        ensure_containers_running(project_root)

        # Start FastAPI in a separate process
        logger.info("Starting FastAPI server")
        proc = multiprocessing.Process(target=run_app)
        proc.start()

        # Give the server time to start
        import time

        time.sleep(5)
        logger.info("Test environment setup completed successfully")

        yield

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
def temp_test_files():
    """
    Fixture for creating and cleaning up temporary test files.
    This runs for each test function that requests it.
    """
    logger.info("Setting up temporary test files")
    root_dir = Path(__file__).parent.parent

    # Create temporary test directories
    temp_dirs = {
        "dynamic": root_dir
        / "games"
        / "prisoners_dilemma"
        / "leagues"
        / "dynamic_test_league",
        "invalid": root_dir / "games" / "invalid_game" / "leagues" / "test_league",
    }

    # Create directories and test files
    for name, path in temp_dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created temporary directory: {name} at {path}")

    # Create test bot file
    test_bot_content = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 'collude'
"""
    test_bot_path = temp_dirs["dynamic"] / "test_bot.py"
    with open(test_bot_path, "w") as f:
        f.write(test_bot_content)
    logger.info(f"Created test bot at {test_bot_path}")

    yield temp_dirs

    # Cleanup temporary files only
    logger.info("Cleaning up temporary test files")
    for path in temp_dirs.values():
        if path.exists():
            shutil.rmtree(path)
            logger.info(f"Removed temporary directory: {path}")


# Provide direct access to test directories
@pytest.fixture
def test_league_path():
    """Access to the protected test_league directory"""
    return REQUIRED_DIRS["prisoners_test"]


@pytest.fixture
def dynamic_test_league_path():
    """Access to the dynamic test league directory"""
    return (
        Path(__file__).parent.parent
        / "games"
        / "prisoners_dilemma"
        / "leagues"
        / "dynamic_test_league"
    )
