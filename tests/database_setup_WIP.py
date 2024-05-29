import os
import sys
from sqlmodel import Session, SQLModel, create_engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models import League, Team, Admin
from auth import get_password_hash
from config import CURRENT_DB, ADMIN_LEAGUE_EXPIRY
from datetime import datetime, timedelta
from database import  add_teams_from_json, League, create_administrator, get_database_url

def create_and_populate_database():
    os.environ["TESTING"] = "1"  # Set the TESTING environment variable to "0"
    DB_URL = get_database_url()
    engine = create_engine(f"sqlite:///{DB_URL.split('///')[1]}")
    print(f"Database URL: {DB_URL}")
    SQLModel.metadata.create_all(engine)
    print("Database with engine created successfully.")


    with Session(engine) as session:
        # Create an admin league called unnassigned
        unnassigned = League(
            name="unassigned",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
            active=True,
            folder="leagues/admin/unassigned",
            game="greedy_pig"
        )
        session.add(unnassigned)
        print("Unassigned league created.")

        comp_test = League(
            name="comp_test",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
            active=True,
            folder="leagues/admin/compt_test",
            game="greedy_pig"
        )
        session.add(comp_test)
        session.commit()

        admin_username = "Administrator"
        admin_password = "BOSSMAN"
        create_administrator(engine, admin_username, admin_password)


        # Create teams from test_teams.json
        teams_json_path = os.path.join(os.path.dirname(__file__), "test_teams.json")
        add_teams_from_json(engine, teams_json_path)
        print("Teams added from test_teams.json")
        session.commit()