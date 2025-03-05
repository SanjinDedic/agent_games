import json
import os
import secrets
from datetime import datetime, timedelta

from sqlmodel import Session, SQLModel, create_engine, select

from backend.config import ADMIN_LEAGUE_EXPIRY, CURRENT_DB, ROOT_DIR
from backend.database.db_models import (
    Admin,
    AgentAPIKey,
    League,
    LeagueType,
    Team,
    TeamType,
    get_password_hash,
)
from backend.routes.user.user_db import save_submission


def create_and_populate_database():
    os.environ["TESTING"] = "0"  # Set the TESTING environment variable to "0"

    engine = create_engine(f"sqlite:///{CURRENT_DB}")
    SQLModel.metadata.drop_all(engine)  # Drop all existing tables
    SQLModel.metadata.create_all(engine)  # Create new tables

    with Session(engine) as session:
        # Create administrator
        admin = Admin(username="admin", password_hash=get_password_hash("admin"))
        session.add(admin)

        # Create unnasigned league
        unassigned_league = League(
            name="unassigned",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
            game="greedy_pig",
            league_type=LeagueType.STUDENT,
        )
        session.add(unassigned_league)

        # create greedy pig league
        greedy_pig_league = League(
            name="greedy_pig_league",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
            game="greedy_pig",
            league_type=LeagueType.STUDENT,
        )
        session.add(greedy_pig_league)

        # create prisoners dilemma league
        prisoners_dilemma_league = League(
            name="prisoners_dilemma_league",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
            game="prisoners_dilemma",
            league_type=LeagueType.STUDENT,
        )
        session.add(prisoners_dilemma_league)

        # Create an agent league for testing
        agent_league = League(
            name="agent_test_league",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
            game="lineup4",
            league_type=LeagueType.AGENT,
        )
        session.add(agent_league)

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
                team_type=TeamType.STUDENT,
            )
            session.add(team)

        # Define initial Lineup4 agent code
        lineup4_code = """
from games.lineup4.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # Simple strategy: choose random valid move
        move = random.choice(game_state["possible_moves"])
        
        # Add custom feedback for monitoring
        self.add_feedback(f"Selected move: {move}")
        
        return move
"""

        # Create two agent teams for Lineup4
        agent_teams = [
            {
                "name": "test_agent1",
                "school_name": "AI Lab Random",
                "code": lineup4_code,
            },
            {
                "name": "test_agent2",
                "school_name": "AI Lab Test",
                "code": lineup4_code,
            },
            {
                "name": "test_agent3",
                "school_name": "AI Lab Test",
                "code": lineup4_code,
            },
            {
                "name": "test_agent4",
                "school_name": "AI Lab Test",
                "code": lineup4_code,
            },
            {
                "name": "test_agent5",
                "school_name": "AI Lab Test",
                "code": lineup4_code,
            },
        ]

        api_keys = []
        for team_data in agent_teams:
            # Create team
            agent_team = Team(
                name=team_data["name"],
                school_name=team_data["school_name"],
                league_id=agent_league.id,
                team_type=TeamType.AGENT,
            )
            session.add(agent_team)
            session.flush()  # To get the team ID

            # Create API key for team
            api_key = secrets.token_urlsafe(32)
            agent_api_key = AgentAPIKey(
                key=api_key, team_id=agent_team.id, is_active=True
            )
            session.add(agent_api_key)
            api_keys.append((team_data["name"], api_key))

            # Create initial submission for team
            save_submission(session, team_data["code"], agent_team.id)

        session.commit()

        print("\nDatabase created and populated successfully")
        print("\n=== Agent Test Credentials ===")
        for team_name, api_key in api_keys:
            print(f"Team Name: {team_name}")
            print(f"API Key: {api_key}")
            print("-----------------------------")


if __name__ == "__main__":
    create_and_populate_database()
