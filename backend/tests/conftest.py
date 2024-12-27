import os
import sys
from pathlib import Path

# Add project root to PYTHONPATH before any imports
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import asyncio
import multiprocessing
import signal

# THEN: All other imports
import warnings

import pytest
import uvicorn

# NOW: Project imports
from api import app
from database import get_db_engine
from docker.containers import ensure_containers_running, stop_containers
from fastapi.testclient import TestClient
from sqlmodel import Session

# Suppress warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings(
        "ignore", category=UserWarning, message=".*error reading bcrypt version.*"
    )


class UvicornTestServer(uvicorn.Server):
    """Uvicorn test server with graceful shutdown"""

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
    server = UvicornTestServer(app)
    server.run()


@pytest.fixture(scope="session", autouse=True)
def start_app():
    # Start containers
    ensure_containers_running(project_root)

    # Start FastAPI in a separate process
    proc = multiprocessing.Process(target=run_app)
    proc.start()

    # Give some time for the server to start
    import time

    time.sleep(5)

    yield

    # Graceful shutdown
    os.kill(proc.pid, signal.SIGINT)
    proc.join(timeout=5)
    if proc.is_alive():
        proc.terminate()
        proc.join()

    stop_containers()


@pytest.fixture(scope="session")
def db_session():
    engine = get_db_engine()
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture(scope="session")
def client(db_session):
    def get_db_session_override():
        return db_session

    app.dependency_overrides[get_db_engine] = get_db_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
