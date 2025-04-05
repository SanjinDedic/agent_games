import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Tuple, Union

import pytz
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, select

from backend.database.db_models import (Institution, League, LeagueType,
                                        SimulationResult, SimulationResultItem,
                                        Submission, Team, TeamType)
from backend.games.game_factory import GameFactory

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


class InstitutionAccessError(Exception):
    """Raised when an institution tries to access data it doesn't own"""
    pass


def create_league(session: Session, league_data, institution_id: int) -> Dict:
    """Create a new league for an institution"""
    # Check if the institution has a league with this name already
    existing_league = session.exec(
        select(League)
        .where(League.name == league_data["name"])
        .where(League.institution_id == institution_id)
    ).first()

    if existing_league:
        raise LeagueExistsError(
            f"League with name '{league_data['name']}' already exists for this institution"
        )

    try:
        # Validate game name
        GameFactory.get_game_class(league_data["game"])

        # Generate unique signup token
        signup_token = secrets.token_urlsafe(16)

        # Create the league
        league = League(
            name=league_data["name"],
            created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
            expiry_date=(
                datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(hours=24)
            ),  # Default 24 hour expiry
            game=league_data["game"],
            institution_id=institution_id,
            league_type=LeagueType.INSTITUTION,
            signup_link=signup_token,
        )

        session.add(league)
        session.flush()
        session.commit()
        return {
            "league_id": league.id,
            "name": league.name,
            "signup_token": signup_token,
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Error creating league: {e}")
        raise


def create_team(session: Session, team_data, institution_id: int) -> Dict:
    """Create a new team for an institution"""
    try:
        # Validate team data
        if not team_data.name or not team_data.password:
            raise TeamError("Team name and password are required")

        # Check for existing team within this institution
        existing_team = session.exec(
            select(Team)
            .where(Team.name == team_data.name)
            .where(Team.institution_id == institution_id)
        ).first()
        
        if existing_team:
            raise TeamError(f"Team with name '{team_data.name}' already exists in this institution")

        # Get unassigned league for this institution
        unassigned_league = session.exec(
            select(League)
            .where(League.name == "unassigned")
            .where(League.institution_id == institution_id)
        ).first()
        
        if not unassigned_league:
            # Create an unassigned league for this institution if it doesn't exist
            unassigned_league = League(
                name="unassigned",
                created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
                expiry_date=(
                    datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(hours=24*7)
                ),
                game="greedy_pig",  # Default game
                institution_id=institution_id,
                league_type=LeagueType.INSTITUTION,
            )
            session.add(unassigned_league)
            session.flush()

        team = Team(
            name=team_data.name,
            school_name=team_data.school_name,
            score=team_data.score,
            color=team_data.color,
            league_id=unassigned_league.id,
            institution_id=institution_id,
            team_type=TeamType.STUDENT,
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
        raise TeamError(f"An unexpected error occurred creating the team: {str(e)}")


def delete_team(session: Session, team_id: int, institution_id: int) -> str:
    """Delete a team and its associated data"""
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    
    if not team:
        raise TeamError(f"Team with ID {team_id} not found")
    
    # Verify the team belongs to this institution
    if team.institution_id != institution_id:
        raise InstitutionAccessError("You don't have permission to delete this team")

    try:
        # Delete associated submissions first
        session.exec(delete(Submission).where(Submission.team_id == team.id))

        # Delete all result items
        session.exec(
            delete(SimulationResultItem).where(SimulationResultItem.team_id == team_id)
        )

        session.delete(team)
        session.commit()

        return f"Team {team.name} deleted successfully"
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting team: {e}")
        raise


def get_all_teams(session: Session, institution_id: int) -> Dict:
    """Get all teams for an institution"""
    try:
        teams = session.exec(
            select(Team).where(Team.institution_id == institution_id)
        ).all()
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


def get_league_by_id(session: Session, league_id: int, institution_id: int) -> League:
    """Get a league by ID, ensuring it belongs to the institution"""
    league = session.exec(select(League).where(League.id == league_id)).first()
    
    if not league:
        raise LeagueNotFoundError(f"League with ID {league_id} not found")
    
    # Verify the league belongs to this institution
    if league.institution_id != institution_id:
        raise InstitutionAccessError("You don't have permission to access this league")
    
    return league


def save_simulation_results(
    session: Session, 
    league_id: int, 
    institution_id: int,
    results: Dict, 
    rewards=None, 
    feedback_str=None, 
    feedback_json=None
) -> SimulationResult:
    """Save simulation results for a league"""
    # Verify the league belongs to this institution
    league = get_league_by_id(session, league_id, institution_id)
    
    timestamp = datetime.now(AUSTRALIA_SYDNEY_TZ)
    rewards_str = rewards if rewards is not None else "[10, 8, 6, 4, 3, 2, 1]"
    if isinstance(rewards_str, list):
        rewards_str = json.dumps(rewards_str)

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
        if team and team.institution_id == institution_id:  # Only include teams from this institution
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


def get_all_league_results(session: Session, league_name: str, institution_id: int) -> Dict:
    """Get all simulation results for a league"""
    league = session.exec(
        select(League)
        .where(League.name == league_name)
        .where(League.institution_id == institution_id)
    ).first()

    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found in your institution")

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
    institution_id: int,
    feedback: Union[str, Dict, None] = None,
) -> Tuple[str, Dict]:
    """Publish simulation results"""
    league = session.exec(
        select(League)
        .where(League.name == league_name)
        .where(League.institution_id == institution_id)
    ).first()

    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found in your institution")

    simulation = session.exec(
        select(SimulationResult).where(SimulationResult.id == sim_id)
    ).first()

    if not simulation:
        raise ValueError(f"Simulation result with ID {sim_id} not found")

    # Verify the simulation belongs to a league in this institution
    if simulation.league_id != league.id:
        raise InstitutionAccessError("You don't have permission to publish this simulation result")

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
    session: Session, league_name: str, expiry_date: datetime, institution_id: int
) -> str:
    """Update league expiry date"""
    league = session.exec(
        select(League)
        .where(League.name == league_name)
        .where(League.institution_id == institution_id)
    ).first()

    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found in your institution")

    try:
        league.expiry_date = expiry_date
        session.add(league)
        session.commit()
        return f"Expiry date updated successfully for league '{league_name}'"

    except Exception as e:
        session.rollback()
        logger.error(f"Error updating expiry date: {e}")
        raise


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


def assign_team_to_league(session: Session, team_id: int, league_id: int, institution_id: int) -> str:
    """Assign a team to a league within the same institution"""
    team = session.get(Team, team_id)
    if not team:
        raise TeamError(f"Team with ID {team_id} not found")

    # Verify the team belongs to this institution
    if team.institution_id != institution_id:
        raise InstitutionAccessError("You don't have permission to modify this team")

    league = session.get(League, league_id)
    if not league:
        raise LeagueNotFoundError(f"League with ID {league_id} not found")

    # Verify the league belongs to this institution
    if league.institution_id != institution_id:
        raise InstitutionAccessError("You don't have permission to assign teams to this league")

    try:
        team.league_id = league.id
        session.add(team)
        session.commit()
        return f"Team '{team.name}' assigned to league '{league.name}'"
    except Exception as e:
        session.rollback()
        logger.error(f"Error assigning team to league: {e}")
        raise


def generate_signup_link(session: Session, league_id: int, institution_id: int) -> Dict:
    """Generate a new signup link for a league"""
    # Get the league
    league = session.get(League, league_id)
    if not league:
        raise LeagueNotFoundError(f"League with ID {league_id} not found")

    # Check if the league belongs to this institution
    if league.institution_id != institution_id:
        raise InstitutionAccessError("You don't have permission to access this league")

    try:
        # Generate a new signup token
        signup_token = secrets.token_urlsafe(16)
        league.signup_link = signup_token
        session.add(league)
        session.commit()

        return {"signup_token": signup_token, "league_name": league.name}
    except Exception as e:
        session.rollback()
        logger.error(f"Error generating signup link: {e}")
        raise


def delete_league(session: Session, league_name: str, institution_id: int) -> str:
    """Delete a league and move its teams to the unassigned league"""
    # Find the league to delete
    league = session.exec(
        select(League)
        .where(League.name == league_name)
        .where(League.institution_id == institution_id)
    ).first()

    if not league:
        raise LeagueNotFoundError(
            f"League '{league_name}' not found in your institution"
        )

    # Can't delete the unassigned league
    if league.name.lower() == "unassigned":
        raise ValueError("Cannot delete the 'unassigned' league")

    # Find the unassigned league for this institution
    unassigned_league = session.exec(
        select(League)
        .where(League.name == "unassigned")
        .where(League.institution_id == institution_id)
    ).first()

    if not unassigned_league:
        # Create an unassigned league if it doesn't exist
        unassigned_league = League(
            name="unassigned",
            created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
            expiry_date=(
                datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=365)  # Long expiry
            ),
            game="greedy_pig",  # Default game
            institution_id=institution_id,
            league_type=LeagueType.INSTITUTION,
        )
        session.add(unassigned_league)
        session.flush()  # Get the ID for the new league

    try:
        # Get all teams in the league
        teams = session.exec(select(Team).where(Team.league_id == league.id)).all()

        team_count = len(teams)

        # Get simulation results for this league
        sim_results = session.exec(
            select(SimulationResult).where(SimulationResult.league_id == league.id)
        ).all()

        # Delete all simulation result items for simulation results in this league
        for sim_result in sim_results:
            session.exec(
                delete(SimulationResultItem).where(
                    SimulationResultItem.simulation_result_id == sim_result.id
                )
            )

        # Delete all simulation results for this league
        session.exec(
            delete(SimulationResult).where(SimulationResult.league_id == league.id)
        )

        # Delete all submissions from teams in this league and move teams to unassigned league
        for team in teams:
            # Delete team's submissions
            session.exec(delete(Submission).where(Submission.team_id == team.id))

            # Move team to unassigned league
            team.league_id = unassigned_league.id
            session.add(team)

        # Delete the league
        session.delete(league)
        session.commit()

        return f"League '{league_name}' deleted and {team_count} teams moved to the unassigned league"

    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting league: {e}")
        raise
