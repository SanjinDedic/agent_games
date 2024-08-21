import os
import shutil
from sqlmodel import Session, SQLModel, create_engine, select
from models_db import League, Team, Admin
from auth import get_password_hash
from config import CURRENT_DB, ADMIN_LEAGUE_EXPIRY, ROOT_DIR
from datetime import datetime, timedelta
from database import create_administrator

def create_and_populate_database():
    os.environ["TESTING"] = "0"  # Set the TESTING environment variable to "0"
    
    engine = create_engine(f"sqlite:///{CURRENT_DB}")
    SQLModel.metadata.drop_all(engine)  # Drop all existing tables
    SQLModel.metadata.create_all(engine)  # Create new tables

    with Session(engine) as session:
        # Create administrator
        create_administrator(session, 'Administrator', 'BOSSMAN')

        # Create admin leagues
        admin_leagues = []
        league_names = ["unassigned", "week1", "week2", "week3"]
        for league_name in league_names:
            league = League(
                name=league_name,
                created_date=datetime.now(),
                expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
                active=True,
                folder=f"leagues/admin/{league_name}",
                game="greedy_pig"
            )
            admin_leagues.append(league)
            
            # Create league folder
            league_folder = os.path.join(ROOT_DIR, "games", "greedy_pig", league.folder)
            os.makedirs(league_folder, exist_ok=True)

        session.add_all(admin_leagues)
        session.commit()

        # Create teams
        players = []
        for i in range(5, 30, 2):
            players.append({
                "name": f"Bank{i}",
                "password": f"bank{i}pass",
                "code": f"""
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] >= {i}:
            return 'bank'
        return 'continue'
"""
            })

        week1_league = session.exec(select(League).where(League.name == "week1")).one()

        for player in players:
            team = Team(
                name=player["name"],
                school_name=f"School of {player['name']}",
                password_hash=get_password_hash(player["password"]),
                league_id=week1_league.id
            )
            session.add(team)
            
            # Create code file for the team
            team_file_path = os.path.join(ROOT_DIR, "games", "greedy_pig", week1_league.folder, f"{player['name']}.py")
            with open(team_file_path, "w") as f:
                f.write(player["code"])

        session.commit()
        print("Database created and populated successfully")

def clean_league_folders():
    for league_name in ["unassigned", "week1", "week2", "week3"]:
        league_folder = os.path.join(ROOT_DIR, "games", "greedy_pig", f"leagues/admin/{league_name}")
        if os.path.exists(league_folder):
            shutil.rmtree(league_folder)
            os.makedirs(league_folder)
    print("League folders have been cleaned.")

if __name__ == "__main__":
    clean_league_folders()
    create_and_populate_database()