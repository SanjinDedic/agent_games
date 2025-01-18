import asyncio
import logging
from datetime import datetime, timedelta
import os
import sys
from typing import Dict, Optional

import aiohttp
from sqlmodel import Session, create_engine, select

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from config import get_database_url
from database.db_models import League, Submission, Team
from games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_auth_token(api_url: str = "http://localhost:8000") -> str:
    """Get authentication token by logging in as admin"""
    try:
        async with aiohttp.ClientSession() as session:
            login_data = {
                "username": "admin",
                "password": "admin"
            }
            async with session.post(f"{api_url}/auth/admin-login", json=login_data) as response:
                if response.status != 200:
                    response_text = await response.text()
                    raise Exception(f"Login failed: {response_text}")
                data = await response.json()
                return data["data"]["access_token"]
    except Exception as e:
        logger.error(f"Error getting auth token: {str(e)}")
        raise

def create_test_submissions(session: Session, league_id: int) -> None:
    """Create some test submissions in the database"""
    try:
        # First, ensure we have test teams
        test_teams = [
            {"name": "TestTeam1", "password": "test123", "school": "Test School 1"},
            {"name": "TestTeam2", "password": "test456", "school": "Test School 2"}
        ]
        
        teams = []
        for team_data in test_teams:
            # Check if team already exists
            existing_team = session.exec(
                select(Team).where(Team.name == team_data["name"])
            ).first()
            
            if not existing_team:
                team = Team(
                    name=team_data["name"],
                    school_name=team_data["school"],
                    league_id=league_id
                )
                team.set_password(team_data["password"])
                session.add(team)
                teams.append(team)
            else:
                # Update existing team's league if needed
                if existing_team.league_id != league_id:
                    existing_team.league_id = league_id
                    session.add(existing_team)
                teams.append(existing_team)
        
        if teams:
            session.commit()

        # Add test submissions for each team
        test_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        my_opponent = game_state["opponent_name"]
        opponent_history = game_state["opponent_history"]
        my_history = game_state["my_history"]
        
        # Add some feedback
        self.add_feedback(f"Playing against {my_opponent}")
        self.add_feedback(f"Round {game_state['round_number']}")
        
        # Always collude for testing
        return 'collude'
"""
        
        for team in teams:
            # Check if submission already exists
            existing_submission = session.exec(
                select(Submission)
                .where(Submission.team_id == team.id)
                .order_by(Submission.timestamp.desc())
            ).first()
            
            if not existing_submission:
                submission = Submission(
                    code=test_code,
                    timestamp=datetime.now(),
                    team_id=team.id
                )
                session.add(submission)
        
        session.commit()
        logger.info(f"Created/updated test submissions in league {league_id}")
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating test submissions: {str(e)}")
        raise

async def run_poc():
    """Main POC function to test API integration"""
    session = None
    try:
        # Set up database connection
        engine = create_engine(get_database_url())
        session = Session(engine)

        # Create a test league if it doesn't exist
        league_name = "api_test_league"
        league = session.exec(
            select(League).where(League.name == league_name)
        ).first()

        if not league:
            league = League(
                name=league_name,
                created_date=datetime.now(),
                expiry_date=datetime.now() + timedelta(days=1),
                folder="leagues/test",
                game="prisoners_dilemma"
            )
            session.add(league)
            session.commit()
            session.refresh(league)
            logger.info(f"Created new test league: {league_name}")
        else:
            logger.info(f"Using existing test league: {league_name}")

        # Create or update test submissions
        create_test_submissions(session, league.id)

        # Get auth token
        auth_token = await get_auth_token()
        logger.info("Successfully obtained auth token")

        # Create game instance
        game = PrisonersDilemmaGame(
            league=league,
            verbose=True,
            rounds_per_pairing=3,
            collect_player_feedback=True
        )

        # Get players via API
        await game.get_all_player_classes_via_api(auth_token=auth_token)

        # Verify players were loaded
        logger.info(f"Loaded {len(game.players)} players:")
        for player in game.players:
            logger.info(f"- {player.name}")

        if len(game.players) < 2:
            raise Exception("Need at least 2 players for a game")

        # Run a test game
        logger.info("Starting test game...")
        game.initialize_histories_and_scores()  # Initialize game state
        results = game.play_game()

        # Log results
        logger.info("\nGame Results:")
        logger.info("-" * 40)
        logger.info("Final Scores:")
        for player_name, score in results["points"].items():
            logger.info(f"{player_name}: {score}")

        # Log player feedback
        if game.player_feedback:
            logger.info("\nPlayer Feedback:")
            logger.info("-" * 40)
            for player_name, feedback in game.player_feedback.items():
                logger.info(f"\n{player_name}'s feedback:")
                for entry in feedback:
                    logger.info(f"Round {entry['round']} vs {entry['opponent']}:")
                    for msg in entry['messages']:
                        logger.info(f"  {msg}")

    except Exception as e:
        logger.error(f"Error in POC: {str(e)}")
        raise
    finally:
        if session:
            session.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_poc())
    except KeyboardInterrupt:
        logger.info("\nPOC stopped by user")
    except Exception as e:
        logger.error(f"POC failed: {str(e)}")