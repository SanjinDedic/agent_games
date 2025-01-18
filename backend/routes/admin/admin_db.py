import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Tuple, Union

import pytz
from config import ROOT_DIR
from database.db_models import (
    League,
    SimulationResult,
    SimulationResultItem,
    Submission,
    Team,
)
from games.game_factory import GameFactory
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, select

logger = logging.getLogger(__name__)
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


class LeagueExistsError(Exception):
    """Raised when attempting to create a league that already exists"""

    pass


class LeagueNotFoundError(Exception):
    """Raised when league is not found"""

    pass


class TeamError(Exception):
    """Base exception for all team-related errors"""

    pass


async def create_league(session: Session, league_data) -> Dict:
    """Create a new league"""
    existing_league = session.exec(
        select(League).where(League.name == league_data.name)
    ).first()

    if existing_league:
        raise LeagueExistsError(f"League with name '{league_data.name}' already exists")

    try:
        # Validate game name
        GameFactory.get_game_class(league_data.game)
    except ValueError:
        raise ValueError(
            f"Invalid game name: {league_data.game}. Available games are: greedy_pig, prisoners_dilemma"
        )

    league_folder = f"leagues/admin/{league_data.name}"

    try:
        league = League(
            name=league_data.name,
            created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
            expiry_date=(
                datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(hours=24)
            ),  # Default 24 hour expiry
            folder=league_folder,
            game=league_data.game,
        )

        session.add(league)
        session.flush()

        # Create league folder
        absolute_folder = os.path.join(ROOT_DIR, "games", league.game, league.folder)
        os.makedirs(absolute_folder, exist_ok=True)

        session.commit()
        return {"league_id": league.id, "name": league.name}

    except Exception as e:
        session.rollback()
        logger.error(f"Error creating league: {e}")
        raise


async def create_team(session: Session, team_data) -> Dict:
    """Create a new team"""
    try:
        # Validate team data
        if not team_data.name or not team_data.password:
            raise TeamError("Team name and password are required")

        # Check for existing team
        existing_team = session.exec(
            select(Team).where(Team.name == team_data.name)
        ).first()
        if existing_team:
            raise TeamError(f"Team with name '{team_data.name}' already exists")

        # Get unassigned league
        unassigned_league = session.exec(
            select(League).where(League.name == "unassigned")
        ).first()
        if not unassigned_league:
            raise TeamError("Unable to assign team to default league")

        team = Team(
            name=team_data.name,
            school_name=team_data.school_name,
            score=team_data.score,
            color=team_data.color,
            league_id=unassigned_league.id,
        )
        team.set_password(team_data.password)

        session.add(team)
        session.commit()

        return {"team_id": team.id, "name": team.name, "school": team.school_name}

    except TeamError as e:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error creating team: {e}")
        raise TeamError("Unable to create team due to data constraints")
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error creating team: {e}")
        raise TeamError("An unexpected error occurred creating the team")


async def delete_team(session: Session, team_name: str) -> str:
    """Delete a team and its associated data"""
    # TODO: Enforcre unique team names
    team = session.exec(select(Team).where(Team.name == team_name)).first()
    if not team:
        raise TeamError(f"Team '{team_name}' not found")

    try:
        # Delete associated submissions first
        session.exec(delete(Submission).where(Submission.team_id == team.id))

        # Delete team's code files if they exist
        if team.league:
            for game_name in ["greedy_pig", "prisoners_dilemma"]:
                team_file = os.path.join(
                    ROOT_DIR, "games", game_name, team.league.folder, f"{team_name}.py"
                )
                if os.path.exists(team_file):
                    os.remove(team_file)

        # Delete the team itself
        session.delete(team)  # Add this line
        session.commit()  # Add this line

        return f"Team '{team_name}' deleted successfully"
    except Exception as e:
        logger.error(f"Error deleting team submissions: {e}")
        raise


async def get_all_teams(session: Session) -> Dict:
    """Get all teams"""
    try:
        teams = session.exec(select(Team)).all()
        return {
            "teams": [
                {
                    "id": team.id,
                    "name": team.name,
                    "school": team.school_name,
                    "league": team.league.name if team.league else None,
                }
                for team in teams
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving teams: {e}")
        raise


async def get_all_league_results(session: Session, league_name: str) -> Dict:
    """Get all simulation results for a league"""
    league = session.exec(select(League).where(League.name == league_name)).first()

    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")

    try:
        results = []
        for sim in league.simulation_results:
            result = await process_simulation_results(sim, league_name)
            results.append(result)

        return {"results": sorted(results, key=lambda x: x["id"], reverse=True)}

    except Exception as e:
        logger.error(f"Error retrieving league results: {e}")
        raise


async def publish_sim_results(
    session: Session,
    league_name: str,
    sim_id: int,
    feedback: Union[str, Dict, None] = None,
) -> Tuple[str, Dict]:
    """Publish simulation results"""
    league = session.exec(select(League).where(League.name == league_name)).first()

    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")

    simulation = session.exec(
        select(SimulationResult).where(SimulationResult.id == sim_id)
    ).first()

    if not simulation:
        raise ValueError(f"Simulation result with ID {sim_id} not found")

    try:
        # Unpublish all other results
        for sim in league.simulation_results:
            sim.published = False
            session.add(sim)

        # Publish this result
        simulation.published = True

        if feedback is not None:
            if isinstance(feedback, str):
                simulation.feedback_str = feedback
                simulation.feedback_json = None
            else:
                simulation.feedback_str = None
                simulation.feedback_json = json.dumps(feedback)

        session.add(simulation)
        session.commit()

        return (
            f"Results published successfully for league '{league_name}'",
            {"sim_id": simulation.id, "league_name": league_name, "published": True},
        )

    except Exception as e:
        session.rollback()
        logger.error(f"Error publishing results: {e}")
        raise


async def update_expiry_date(
    session: Session, league_name: str, expiry_date: datetime
) -> str:
    """Update league expiry date"""
    league = session.exec(select(League).where(League.name == league_name)).first()

    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")

    try:
        league.expiry_date = expiry_date
        session.add(league)
        session.commit()
        return f"Expiry date updated successfully for league '{league_name}'"

    except Exception as e:
        session.rollback()
        logger.error(f"Error updating expiry date: {e}")
        raise


async def save_simulation_results(
    session, league_id, results, rewards=None, feedback_str=None, feedback_json=None
):
    timestamp = datetime.now(AUSTRALIA_SYDNEY_TZ)

    rewards_str = (
        json.dumps(rewards) if rewards is not None else "[10, 8, 6, 4, 3, 2, 1]"
    )

    simulation_result = SimulationResult(
        league_id=league_id,
        timestamp=timestamp,
        num_simulations=results["num_simulations"],
        custom_rewards=rewards_str,
        feedback_str=feedback_str,
        feedback_json=feedback_json,
    )
    session.add(simulation_result)
    session.flush()

    custom_value_names = list(results.get("table", {}).keys())[:3]

    for team_name, score in results["total_points"].items():
        team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
        if team:
            result_item = SimulationResultItem(
                simulation_result_id=simulation_result.id, team_id=team.id, score=score
            )

            for i, name in enumerate(custom_value_names, start=1):
                value = results["table"][name]
                if isinstance(value, dict):
                    setattr(result_item, f"custom_value{i}", value.get(team_name))
                else:
                    setattr(result_item, f"custom_value{i}", value)
                setattr(result_item, f"custom_value{i}_name", name)

            session.add(result_item)

    session.commit()
    return simulation_result


async def process_simulation_results(sim: SimulationResult, league_name: str) -> Dict:
    """Helper function to process simulation results"""
    total_points = {}
    table_data = {}

    for result in sim.simulation_results:
        team_name = result.team.name
        total_points[team_name] = result.score

        for i in range(1, 4):
            custom_value = getattr(result, f"custom_value{i}")
            custom_value_name = getattr(result, f"custom_value{i}_name")

            if custom_value_name:
                if custom_value_name not in table_data:
                    table_data[custom_value_name] = {}
                table_data[custom_value_name][team_name] = custom_value

    feedback = None
    if sim.feedback_str:
        feedback = sim.feedback_str
    elif sim.feedback_json:
        feedback = json.loads(sim.feedback_json)

    return {
        "id": sim.id,
        "league_name": league_name,
        "timestamp": sim.timestamp,
        "total_points": total_points,
        "table": table_data,
        "num_simulations": sim.num_simulations,
        "rewards": json.loads(sim.custom_rewards),
        "feedback": feedback,
    }


async def get_league(session, league_name):
    league = session.exec(
        select(League).where(League.name == league_name)
    ).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")
    return league
