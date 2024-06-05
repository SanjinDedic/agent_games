import os
from sqlmodel import Session, SQLModel, create_engine
from models import League, Team, Admin
from auth import get_password_hash
from config import CURRENT_DB, ADMIN_LEAGUE_EXPIRY
from datetime import datetime, timedelta
from database import create_administrator

def create_and_populate_database():
    os.environ["TESTING"] = "0"  # Set the TESTING environment variable to "0"
    
    engine = create_engine(f"sqlite:///{CURRENT_DB}")
    SQLModel.metadata.create_all(engine)


    with Session(engine) as session:
        # Create an admin league called unnassigned
        create_administrator(session, 'Administrator', 'BOSSMAN')
        admin_leagues = []
        unnassigned = League(
            name="unassigned",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
            active=True,
            folder="leagues/admin/unassigned",
            game="greedy_pig"
        )
        admin_leagues.append(unnassigned)
        for i in range(1, 4):
            league_name = f"week{i}"
            league = League(
                name=league_name,
                created_date=datetime.now(),
                expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
                active=True,
                folder=f"leagues/admin/{league_name}",
                game="greedy_pig"
            )
            admin_leagues.append(league)
        session.add_all(admin_leagues)



        # Create 12 teams with their passwords
        teams = [
            {"name": "team1", "password": "pass1"},
            {"name": "team2", "password": "pass2"},
            {"name": "team3", "password": "pass3"},
            {"name": "team4", "password": "pass4"},
            {"name": "team5", "password": "pass5"},
            {"name": "team6", "password": "pass6"},
            {"name": "team7", "password": "pass7"},
            {"name": "team8", "password": "pass8"},
            {"name": "team9", "password": "pass9"},
            {"name": "team10", "password": "pass10"},
            {"name": "team11", "password": "pass11"},
            {"name": "team12", "password": "pass12"}
        ]

        for team_data in teams:
            team = Team(
                name=team_data["name"],
                school_name=f"School {team_data['name']}",
                password_hash=get_password_hash(team_data["password"]),
                league_id=1
            )
            session.add(team)

        session.commit()

        print("Database populated successfully.")

if __name__ == "__main__":
    create_and_populate_database()
