import json
import os
from datetime import datetime, timedelta

from database.db_models import get_password_hash
from config import ADMIN_LEAGUE_EXPIRY, CURRENT_DB, ROOT_DIR

from database.db_models import League, Team, Admin
from sqlmodel import Session, SQLModel, create_engine, select

def create_validation_leagues(session: Session):
    """Create validation leagues for each game type"""
    games = ["greedy_pig", "prisoners_dilemma"]  # Could be fetched from config
    for game in games:
        validation_league = League(
            name=f"{game}_validation",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(days=36500)),  # Set far in future
            active=True,
            game=game,
            is_validation=True
        )
        session.add(validation_league)
    session.commit()

def create_and_populate_database():
    os.environ["TESTING"] = "0"  # Set the TESTING environment variable to "0"

    engine = create_engine(f"sqlite:///{CURRENT_DB}")
    SQLModel.metadata.drop_all(engine)  # Drop all existing tables
    SQLModel.metadata.create_all(engine)  # Create new tables

    with Session(engine) as session:
        # Create administrator
        admin = Admin(username="admin", password_hash=get_password_hash("admin"))
        session.add(admin)
        
        # Create validation leagues
        create_validation_leagues(session)
        
        # Create unnasigned league
        unassigned_league = League(
            name="unassigned",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
            game="greedy_pig",
        )
        session.add(unassigned_league)

        #create greedy pig league

        greedy_pig_league = League(
            name="greedy_pig_league",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
            game="greedy_pig"
        )
        session.add(greedy_pig_league)

        #create prisoners dilemma league

        prisoners_dilemma_league = League(
            name="prisoners_dilemma_league",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
            game="prisoners_dilemma"
        )

        session.add(prisoners_dilemma_league)

        session.commit()

        # Get the unassigned league
        unassigned_league = session.exec(
            select(League).where(League.name == "unassigned")
        ).one()

        # Read teams from teams.json
        with open(os.path.join(ROOT_DIR, "teams.json"), "r") as f:
            teams_data = json.load(f)

        # Create teams
        for team_data in teams_data["teams"]:
            team = Team(
                name=team_data["name"],
                school_name=team_data["school"],
                password_hash=get_password_hash(team_data["password"]),
                league_id=unassigned_league.id,
            )
            session.add(team)

        session.commit()
        print("Database created and populated successfully")

if __name__ == "__main__":
    create_and_populate_database()