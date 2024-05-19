import os
import sys
import pytest
import time
import shutil
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session, select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from models import League, Team, Submission
from tests.database_setup import setup_test_db

os.environ["TESTING"] = "1"

TEAM_TOKEN = ""

@pytest.fixture(scope="session")
def db_engine():
    engine = setup_test_db(verbose=True)
    yield engine
    try:
        if os.path.exists("../test.db"):
            os.remove("../test.db")
        else:
            os.remove("test.db")
    except FileNotFoundError:
        pass
    finally:
        time.sleep(1)

@pytest.fixture(scope="function")
def db_session(db_engine: Engine):
    with Session(db_engine) as session:
        yield session
        session.rollback()

@pytest.fixture(scope="function")
def client(db_session: Session):
    def get_db_session_override():
        return db_session

    app.dependency_overrides[get_db_engine] = get_db_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_submit_agent(client: TestClient, db_session: Session):
    global TEAM_TOKEN

    # Get the token for the team
    team_login_response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"})
    assert team_login_response.status_code == 200
    TEAM_TOKEN = team_login_response.json()["access_token"]

    # Submit code for the team
    code = "print('Hello, World!')"
    submission_response = client.post(
        "/submit_agent",
        json={"code": code},
        headers={"Authorization": f"Bearer {TEAM_TOKEN}"}
    )
    assert submission_response.status_code == 200
    assert "Code submitted successfully." in submission_response.json()["message"]

    # Check if the submission is saved in the database
    statement = db_session.exec(select(Submission))
    submissions = statement.fetchall()
    assert len(submissions) == 1
    assert submissions[0].code == code
    assert submissions[0].team.name == "BrunswickSC1"
    shutil.rmtree("leagues", ignore_errors=True)

