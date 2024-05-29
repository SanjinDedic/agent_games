import os
import sys
import pytest
import json
import time
from sqlmodel import Session, SQLModel, create_engine

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models import League, Team, Admin
from auth import get_password_hash
from config import CURRENT_DB, ADMIN_LEAGUE_EXPIRY
from datetime import datetime, timedelta
from database import add_teams_from_json, League, create_administrator, get_database_url

@pytest.fixture(scope="function")
def db_engine():
    os.environ["TESTING"] = "1"  # Set the TESTING environment variable to "1"
    DB_URL = get_database_url()
    engine = create_engine(f"sqlite:///{DB_URL.split('///')[1]}")
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()
    os.remove(DB_URL.split("///")[1])  # Remove the test database file

@pytest.fixture(scope="function")
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session
        session.rollback()

def setup_test_db(db_session):
    # Create an admin league called unassigned
    unnassigned = League(
        name="unassigned",
        created_date=datetime.now(),
        expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
        active=True,
        folder="leagues/admin/unassigned",
        game="greedy_pig"
    )
    db_session.add(unnassigned)
    print("Unassigned league created.")

    comp_test = League(
        name="comp_test",
        created_date=datetime.now(),
        expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
        active=True,
        folder="leagues/admin/compt_test",
        game="greedy_pig"
    )
    db_session.add(comp_test)
    db_session.commit()

    admin_username = "Administrator"
    admin_password = "BOSSMAN"
    create_administrator(db_engine, admin_username, admin_password)

    # Create teams from test_teams.json
    teams_json_path = os.path.join(os.path.dirname(__file__), "test_teams.json")
    with open (teams_json_path, "r") as file:
        data = json.load(file)
        teams = data["teams"]
        for team in teams:
            name = team["name"]
            password = team["password"]
            school = team["school"]
            new_team = Team()


    print("Teams added from test_teams.json")
    db_session.commit()