import json
import logging

from datetime import datetime, timedelta
from typing import Dict

import pytz

from backend.database.db_models import League, Submission, Team
from sqlmodel import Session, select

logger = logging.getLogger(__name__)
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


class SubmissionLimitExceededError(Exception):
    """Raised when submission rate limit is exceeded"""

    pass


class TeamNotFoundError(Exception):
    """Raised when team is not found"""

    pass


class LeagueNotFoundError(Exception):
    """Raised when league is not found"""

    pass


def allow_submission(session: Session, team_id: int) -> bool:
    """Check if team is allowed to submit (rate limiting)"""
    one_minute_ago = datetime.now(AUSTRALIA_SYDNEY_TZ) - timedelta(minutes=1)
    recent_submissions = session.exec(
        select(Submission)
        .where(Submission.team_id == team_id)
        .where(Submission.timestamp >= one_minute_ago)
    ).all()

    if len(recent_submissions) > 5:
        raise SubmissionLimitExceededError(
            "You can only make 5 submissions per minute."
        )
    return True


def save_submission(session: Session, code: str, team_id: int) -> int:
    """Save a code submission"""
    db_submission = Submission(
        code=code,
        timestamp=datetime.now(AUSTRALIA_SYDNEY_TZ),
        team_id=team_id,
    )
    session.add(db_submission)
    session.commit()
    return db_submission.id


def assign_team_to_league(session: Session, team_name: str, league_name: str) -> str:
    """Assign a team to a league"""
    league = session.exec(
        select(League).where(League.name == league_name)
    ).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")

    team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
    if not team:
        raise TeamNotFoundError(f"Team '{team_name}' not found")

    team.league_id = league.id
    session.add(team)
    session.commit()
    session.refresh(team)
    return f"Team '{team.name}' assigned to league '{league.name}'"


def get_published_result(session: Session, league_name: str) -> dict:
    """Get published results for a specific league"""
    league = session.exec(
        select(League).where(League.name == league_name)
    ).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")

    active = False
    expiry_date = league.expiry_date
    if expiry_date.tzinfo is None:
        expiry_date = AUSTRALIA_SYDNEY_TZ.localize(expiry_date)
    if expiry_date > datetime.now(AUSTRALIA_SYDNEY_TZ):
        active = True

    for sim in league.simulation_results:
        if sim.published:
            total_points = {}
            table = {}
            num_simulations = sim.num_simulations
            for result in sim.simulation_results:
                total_points[result.team.name] = result.score
                for i in range(1, 4):
                    value_name = getattr(result, f"custom_value{i}_name")
                    value = getattr(result, f"custom_value{i}")
                    if value_name:
                        if value_name not in table:
                            table[value_name] = {}
                        table[value_name][result.team.name] = value

            feedback = None
            if sim.feedback_str is not None:
                feedback = sim.feedback_str
            elif sim.feedback_json is not None:
                feedback = json.loads(sim.feedback_json)

            return {
                "league_name": league_name,
                "id": sim.id,
                "total_points": total_points,
                "table": table,
                "num_simulations": num_simulations,
                "active": active,
                "rewards": json.loads(sim.custom_rewards),
                "feedback": feedback,
            }

    return None


def get_all_published_results(session: Session) -> dict:
    """Get all published results across leagues"""
    current_time = datetime.now(AUSTRALIA_SYDNEY_TZ)
    all_results = []

    leagues = session.exec(select(League)).all()
    for league in leagues:
        expiry_date = league.expiry_date
        if expiry_date.tzinfo is None:
            expiry_date = AUSTRALIA_SYDNEY_TZ.localize(expiry_date)
        active = expiry_date >= current_time

        for sim in league.simulation_results:
            if sim.published:
                result = process_simulation_results(sim, league.name, active)
                all_results.append(result)

    return {"all_results": all_results}


def process_simulation_results(sim, league_name: str, active: bool = None) -> dict:
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
    if sim.feedback_str is not None:
        feedback = sim.feedback_str
    elif sim.feedback_json is not None:
        feedback = json.loads(sim.feedback_json)

    result_data = {
        "league_name": league_name,
        "id": sim.id,
        "total_points": total_points,
        "table": table_data,
        "num_simulations": sim.num_simulations,
        "timestamp": sim.timestamp,
        "rewards": sim.custom_rewards,
        "feedback": feedback,
    }

    if active is not None:
        result_data["active"] = active

    return result_data


# routes/user/user_db.py


def get_all_leagues(session: Session) -> Dict:
    """Get all leagues - reusing existing query logic"""
    try:
        leagues = session.exec(select(League)).all()
        return {
            "leagues": [
                {
                    "id": league.id,
                    "name": league.name,
                    "game": league.game,
                    "created_date": league.created_date,
                    "expiry_date": league.expiry_date,
                    "folder": league.folder,
                }
                for league in leagues
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving leagues: {e}")
        raise


def get_team(session, team_name):
    team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
    if not team:
        raise TeamNotFoundError(f"Team '{team_name}' not found")
    return team
