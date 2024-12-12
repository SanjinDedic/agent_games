import json
import os
from datetime import datetime, timedelta

from auth import get_password_hash
from config import ADMIN_LEAGUE_EXPIRY
from database import get_database_url
from models_db import Admin, League, Submission, Team
from sqlmodel import Session, SQLModel, create_engine, delete


def db_engine():
    os.environ["TESTING"] = "1"  # Set the TESTING environment variable to "1"
    DB_URL = get_database_url()
    engine = create_engine(f"sqlite:///{DB_URL.split('///')[1]}")
    SQLModel.metadata.create_all(engine)
    return engine


def setup_test_db(engine=db_engine()):
    with Session(engine) as session:
        if not os.path.exists(get_database_url()):
            session.exec(delete(Team))
            session.exec(delete(League))
            session.exec(delete(Admin))
            session.exec(delete(Submission))
            session.commit()

        # Create an admin league called unassigned
        unnassigned = League(
            name="unassigned",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
            active=True,
            folder="leagues/admin/unassigned",
            game="greedy_pig",
        )
        session.add(unnassigned)
        print("Unassigned league created.")

        comp_test = League(
            name="comp_test",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
            active=True,
            folder="leagues/admin/comp_test",
            game="greedy_pig",
        )
        session.add(comp_test)
        session.commit()

        admin_username = "Administrator"
        admin_password = "BOSSMAN"
        hashed_password = get_password_hash(admin_password)
        print("hashedpw", hashed_password)
        admin = Admin(username=admin_username, password_hash=hashed_password)
        session.add(admin)

        # Create teams from test_teams.json
        teams_json_path = os.path.join(os.path.dirname(__file__), "test_teams.json")
        with open(teams_json_path, "r") as file:
            data = json.load(file)
            teams = data["teams"]
            for team in teams:
                name = team["name"]
                password = team["password"]
                school = team["school"]
                new_team = Team(
                    name=name,
                    password_hash=get_password_hash(password),
                    school_name=school,
                    league_id=2,
                )
                session.add(new_team)

        session.commit()

        # Create 12 teams with their passwords
        teams = [
            {"name": "AlwaysBank", "password": "pass1"},
            {"name": "Bank5", "password": "pass2"},
            {"name": "Bank10", "password": "pass3"},
            {"name": "Bank15", "password": "pass4"},
            {"name": "BankRoll3", "password": "pass5"},
            {"name": "team6", "password": "pass6"},
            {"name": "team7", "password": "pass7"},
            {"name": "team8", "password": "pass8"},
            {"name": "team9", "password": "pass9"},
            {"name": "team10", "password": "pass10"},
            {"name": "team11", "password": "pass11"},
            {"name": "team12", "password": "pass12"},
        ]

        for team_data in teams:
            team = Team(
                name=team_data["name"],
                school_name=f"School {team_data['name']}",
                password_hash=get_password_hash(team_data["password"]),
                league_id=2,
            )
            session.add(team)

        session.commit()

    """
    TO DO:
    1. create a test db file
    2. create a test db engine
    3. use with Session(engine) as session:
    4. create an admin league called unassigned
    5. create an admin league called comp_test
    6. Create an Administrator if it doesn't exist 
    7. Creaate teams from test_teams.json

    """


if __name__ == "__main__":
    setup_test_db()
    print("Database setup complete.")
