import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, Union

import pytz
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, select

from backend.config import ROOT_DIR
from backend.database.db_models import (
    AgentAPIKey,
    DemoUser,
    League,
    LeagueType,
    SimulationResult,
    SimulationResultItem,
    Submission,
    Team,
    TeamType,
)
from backend.games.game_factory import GameFactory
from backend.routes.admin.admin_models import CreateAgentTeam

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


def create_league(session: Session, league_data) -> Dict:
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

    try:
        league = League(
            name=league_data.name,
            created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
            expiry_date=(
                datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(hours=24)
            ),  # Default 24 hour expiry
            game=league_data.game,
        )

        session.add(league)
        session.flush()
        session.commit()
        return {"league_id": league.id, "name": league.name}

    except Exception as e:
        session.rollback()
        logger.error(f"Error creating league: {e}")
        raise


def create_team(session: Session, team_data) -> Dict:
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


def delete_team(session: Session, team_id: str) -> str:
    """Delete a team and its associated data"""
    # TODO: Enforcre unique team names
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise TeamError(f"Team with team_id'{team_id}' not found")

    try:
        # Delete associated submissions first
        session.exec(delete(Submission).where(Submission.team_id == team.id))

        # Delete all result items
        session.exec(
            delete(SimulationResultItem).where(SimulationResultItem.team_id == team_id)
        )

        session.delete(team)
        session.commit()

        return f"Team with team_id: {team_id} deleted successfully"
    except Exception as e:
        logger.error(f"Error deleting team submissions: {e}")
        raise


def get_all_teams(session: Session) -> Dict:
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


def get_all_league_results(session: Session, league_name: str) -> Dict:
    """Get all simulation results for a league"""
    league = session.exec(select(League).where(League.name == league_name)).first()

    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")

    try:
        results = []
        for sim in league.simulation_results:
            result = process_simulation_results(sim, league_name)
            results.append(result)

        return {"results": sorted(results, key=lambda x: x["id"], reverse=True)}

    except Exception as e:
        logger.error(f"Error retrieving league results: {e}")
        raise


def publish_sim_results(
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


def update_expiry_date(
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


def save_simulation_results(
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


def process_simulation_results(sim: SimulationResult, league_name: str) -> Dict:
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


def get_league_by_name(session, league_name):
    league = session.exec(
        select(League).where(League.name == league_name)
    ).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")
    return league


def get_league_by_id(session, league_id):
    league = session.exec(select(League).where(League.id == league_id)).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League with league id {league_id} not found")
    return league


# In backend/routes/admin/admin_db.py

import secrets


def create_agent_team(session: Session, team_data: CreateAgentTeam) -> Dict:
    """Create a new agent team"""
    try:
        # Check if league exists and is agent type
        league = session.get(League, team_data.league_id)
        if not league:
            raise ValueError(f"League with ID {team_data.league_id} not found")
        if league.league_type != LeagueType.AGENT:
            raise ValueError("Can only create agent teams in agent leagues")

        # Create team
        team = Team(
            name=team_data.name,
            school_name="AI Agent",
            team_type=TeamType.AGENT,
            league_id=team_data.league_id,
        )
        session.add(team)
        session.commit()
        session.refresh(team)

        return {"team_id": team.id, "name": team.name, "league": league.name}

    except Exception as e:
        session.rollback()
        raise


def create_api_key(session: Session, team_id: int) -> Dict:
    """Create a new API key for an agent team"""
    try:
        team = session.get(Team, team_id)
        if not team:
            raise ValueError(f"Team with ID {team_id} not found")
        if team.team_type != TeamType.AGENT:
            raise ValueError("Can only create API keys for agent teams")

        # Generate secure API key
        api_key = secrets.token_urlsafe(32)

        # Create API key record
        key_record = AgentAPIKey(key=api_key, team_id=team_id)
        session.add(key_record)
        session.commit()

        return {"team_id": team_id, "api_key": api_key}

    except Exception as e:
        session.rollback()
        raise


def get_all_demo_users(session: Session):
    """
    Get all demo users with their last played league, last submission timestamp,
    and total number of submissions.

    Returns:
        List of dictionaries containing:
        - team_name: Demo user's team name
        - league_name: Last league the demo user played in
        - last_submission: Timestamp of the last submission
        - submission_count: Total number of submissions by the demo user
    """
    try:
        demo_teams = session.exec(select(Team).where(Team.is_demo == True)).all()
        result = []
        if len(demo_teams) == 0:
            return {"demo_users": []}

        for team in demo_teams:
            latest_submission = session.exec(
                select(Submission)
                .where(Submission.team_id == team.id)
                .order_by(Submission.timestamp.desc())
            ).first()
            # Add a null check before accessing .timestamp
            latest_submission_timestamp = None
            if latest_submission is not None:
                latest_submission_timestamp = latest_submission.timestamp
            # get the email from the DemoUser table
            matching_demo_user = session.exec(
                select(DemoUser).where(DemoUser.username == team.school_name)
            ).first()  # for the special case of demo users, the username they typed in is saved as the school_name
            email = matching_demo_user.email if matching_demo_user is not None else None
            result.append(
                {
                    "demo_team_id": team.id,
                    "demo_team_name": team.name,
                    "email": email,
                    "league_name": team.league.name,
                    "number_of_submissions": len(team.submissions),
                    "latest_submission": latest_submission_timestamp,
                }
            )
        return {"demo_users": result}

    except Exception as e:
        session.rollback()
        raise


def delete_all_demo_teams_and_subs(session):
    all_demo_teams = session.exec(select(Team).where(Team.is_demo == True)).all()

    team_ids = [team.id for team in all_demo_teams]

    # First, delete all submissions from these teams
    session.exec(delete(Submission).where(Submission.team_id.in_(team_ids)))
    # Delete any SimulationResultItems for these teams
    session.exec(
        delete(SimulationResultItem).where(SimulationResultItem.team_id.in_(team_ids))
    )
    # Now delete the teams themselves
    session.exec(delete(Team).where(Team.id.in_(team_ids)))

    session.commit()
