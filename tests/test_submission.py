import os
import sys
import pytest
import time
from fastapi.testclient import TestClient
from sqlmodel import Session
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import ROOT_DIR
from api import app
from database import get_db_engine
from models_db import League, Submission
from tests.database_setup import setup_test_db
from sqlmodel import select
os.environ["TESTING"] = "1"

ADMIN_VALID_TOKEN = ""

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    setup_test_db()

@pytest.fixture(scope="function")
def db_session():
    engine = get_db_engine()
    with Session(engine) as session:
        yield session
        session.rollback()

@pytest.fixture(scope="function")
def client(db_session):
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
    TEAM_TOKEN = team_login_response.json()["data"]["access_token"]

    # Submit code for the team
    code = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 15:
            return 'bank'
        return 'continue'
"""
    submission_response = client.post(
        "/submit_agent",
        json={"code": code, "team_name": "BrunswickSC1", "league_name": "comp_test"},
        headers={"Authorization": f"Bearer {TEAM_TOKEN}"}
    )
    print("Submission Response:", submission_response.json()) 
    assert submission_response.status_code == 200
    assert "Code submitted successfully." in submission_response.json()["message"]

    # Check if the submission is saved in the database
    submission = db_session.exec(select(Submission).where(Submission.code == code)).one_or_none()
    assert submission is not None
    assert submission.team_id == 2  # Assuming the team ID is 2 for "BrunswickSC1"

    # Delete the submission
    print("deleting submission from", f"{ROOT_DIR}/games/greedy_pig/leagues/admin/comp_test/BrunswickSC1.py")
    os.remove(f"{ROOT_DIR}/games/greedy_pig/leagues/admin/comp_test/BrunswickSC1.py")