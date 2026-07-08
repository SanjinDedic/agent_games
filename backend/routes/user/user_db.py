import json
import logging
from datetime import timedelta
from typing import Dict, Optional

from sqlmodel import Session, select

from backend.database.db_models import (
    League,
    Submission,
    SubmissionMetadata,
    Team,
    TeamType,
    SimulationResult,
)
from backend.time_utils import ensure_utc, utc_now
from backend.utils import process_simulation_results


class TeamError(Exception):
    """Base exception for all team-related errors"""

    pass


logger = logging.getLogger(__name__)


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
    team = session.get(Team, team_id)
    if not team:
        raise TeamNotFoundError(f"Team with ID {team_id} not found")

    one_minute_ago = utc_now() - timedelta(minutes=1)
    recent_submissions = session.exec(
        select(SubmissionMetadata)
        .where(SubmissionMetadata.team_id == team_id)
        .where(SubmissionMetadata.timestamp >= one_minute_ago)
    ).all()

    # Demo users get a higher submission limit (10 per minute instead of 5)
    max_submissions = 5

    if len(recent_submissions) >= max_submissions:
        raise SubmissionLimitExceededError(
            f"You can only make {max_submissions} submissions per minute."
        )
    return True


def record_failed_submission(
    session: Session,
    team_id: int,
    league_id: Optional[int] = None,
    duration_ms: Optional[float] = None,
    hint_included: bool = False,
) -> int:
    """Record an attempt that failed validation. Code is not stored."""
    meta = SubmissionMetadata(
        team_id=team_id,
        league_id=league_id,
        timestamp=utc_now(),
        duration_ms=duration_ms,
        hint_included=hint_included,
    )
    session.add(meta)
    session.commit()
    return meta.id


def save_submission(
    session: Session,
    code: str,
    team_id: int,
    league_id: Optional[int] = None,
    duration_ms: Optional[float] = None,
    hint_included: bool = False,
) -> int:
    """Record a validated attempt: metadata row plus linked code row."""
    now = utc_now()
    meta = SubmissionMetadata(
        team_id=team_id,
        league_id=league_id,
        timestamp=now,
        duration_ms=duration_ms,
        hint_included=hint_included,
    )
    session.add(meta)
    session.flush()
    db_submission = Submission(code=code, timestamp=now, metadata_id=meta.id)
    session.add(db_submission)
    session.commit()
    return db_submission.id


def assign_team_to_league(
    session: Session, team_id: int, league_id: int, is_demo: bool
) -> str:
    """Assign a team to a league"""
    league = session.get(League, league_id)
    if not league:
        raise LeagueNotFoundError(f"League with ID {league_id} not found")

    if is_demo and not league.is_demo:
        raise ValueError("Demo users can only join demo leagues")

    team = session.get(Team, team_id)
    if not team:
        raise TeamNotFoundError(f"Team with ID {team_id} not found")

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
    if ensure_utc(league.expiry_date) > utc_now():
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
    current_time = utc_now()
    all_results = []

    leagues = session.exec(select(League)).all()
    for league in leagues:
        active = ensure_utc(league.expiry_date) >= current_time

        for sim in league.simulation_results:
            if sim.published:
                result = process_simulation_results(sim, league.name, active)
                all_results.append(result)

    return {"all_results": all_results}


def get_all_published_results_for_league(session: Session, league_id: int) -> dict:
    """Get all published results for a single league, newest first."""
    league = session.get(League, league_id)
    if not league:
        raise LeagueNotFoundError(f"League with ID {league_id} not found")

    active = ensure_utc(league.expiry_date) >= utc_now()

    results = [
        process_simulation_results(sim, league.name, active)
        for sim in league.simulation_results
        if sim.published
    ]
    results.sort(key=lambda r: r["id"], reverse=True)
    return {
        "league_name": league.name,
        "info_markdown": league.info_markdown or "",
        "all_results": results,
    }


def get_all_leagues(session: Session):
    """Get all leagues"""
    leagues = session.exec(select(League).where(League.deleted_date == None)).all()

    return {
        "leagues": [
            {
                "id": league.id,
                "name": league.name,
                "game": league.game,
                "created_date": league.created_date,
                "expiry_date": league.expiry_date,
                "signup_link": league.signup_link,
            }
            for league in leagues
        ]
    }


def get_leagues_for_user(session: Session, role: str, institution_id: Optional[int]):
    """Get leagues scoped to the user's institution. Admin sees all."""
    query = select(League).where(League.deleted_date == None)

    if role != "admin":
        if institution_id is not None:
            query = query.where(League.institution_id == institution_id)
        else:
            return {"leagues": []}

    leagues = session.exec(query).all()

    return {
        "leagues": [
            {
                "id": league.id,
                "name": league.name,
                "game": league.game,
                "created_date": league.created_date,
                "expiry_date": league.expiry_date,
                "signup_link": league.signup_link,
                "institution_name": league.institution.name if league.institution else None,
                "info_markdown": league.info_markdown or "",
            }
            for league in leagues
        ]
    }


def get_team_by_id(session: Session, team_id: int) -> Team:
    team = session.get(Team, team_id)
    if not team:
        raise TeamNotFoundError(f"Team with ID {team_id} not found")
    return team


def get_latest_submissions_for_league(
    session: Session, league_id: int
) -> Dict[str, str]:
    """Get latest submissions for all teams in a league"""
    teams = session.exec(select(Team).where(Team.league_id == league_id)).all()

    submissions = {}
    for team in teams:
        # Get latest submission for each team
        latest_submission = session.exec(
            select(Submission)
            .join(SubmissionMetadata, Submission.metadata_id == SubmissionMetadata.id)
            .where(SubmissionMetadata.team_id == team.id)
            .order_by(Submission.timestamp.desc())
            .limit(1)
        ).first()

        if latest_submission:
            submissions[team.name] = latest_submission.code

    logger.info(f"Found {len(submissions)} submissions for league {league_id}")
    return submissions


def get_all_submissions_for_league(
    session: Session, league_id: int
) -> Dict[str, Dict]:
    """Get all submissions for all teams in a league, ordered by timestamp.

    Returns {"teams": {team_name: [submission, ...]}, "team_ids": {team_name: team_id}}.
    """
    teams = session.exec(select(Team).where(Team.league_id == league_id)).all()

    by_team = {}
    team_ids = {}
    for team in teams:
        rows = session.exec(
            select(Submission, SubmissionMetadata)
            .join(SubmissionMetadata, Submission.metadata_id == SubmissionMetadata.id)
            .where(SubmissionMetadata.team_id == team.id)
            .order_by(Submission.timestamp.asc())
        ).all()

        by_team[team.name] = [
            {
                "code": sub.code,
                "timestamp": sub.timestamp.isoformat(),
                "id": sub.id,
                "duration_ms": meta.duration_ms,
            }
            for sub, meta in rows
        ]
        team_ids[team.name] = team.id

    logger.info(f"Found submissions for {len(by_team)} teams in league {league_id}")
    return {"teams": by_team, "team_ids": team_ids}


def get_team_submission(
    session: Session, team_id: int, league_id: Optional[int] = None
) -> Dict[str, Optional[str]]:
    """Get latest submission for a specific team, scoped to the given league."""
    query = (
        select(Submission)
        .join(SubmissionMetadata, Submission.metadata_id == SubmissionMetadata.id)
        .where(SubmissionMetadata.team_id == team_id)
    )
    if league_id is not None:
        query = query.where(SubmissionMetadata.league_id == league_id)
    submission = session.exec(
        query.order_by(Submission.timestamp.desc()).limit(1)
    ).first()

    return {"code": submission.code if submission else None}


def get_team_submission_history(session: Session, team_id: int) -> list:
    """Get full submission history for a team, newest first."""

    rows = session.exec(
        select(Submission, SubmissionMetadata)
        .join(SubmissionMetadata, Submission.metadata_id == SubmissionMetadata.id)
        .where(SubmissionMetadata.team_id == team_id)
        .order_by(Submission.timestamp.desc())
    ).all()

    return [
        {
            "id": sub.id,
            "code": sub.code,
            "timestamp": sub.timestamp.isoformat(),
            "duration_ms": meta.duration_ms,
        }
        for sub, meta in rows
    ]


def get_league_by_signup_token(session: Session, signup_token: str) -> League:
    """Get a league by its signup token"""
    league = session.exec(
        select(League).where(League.signup_link == signup_token)
    ).first()
    if not league:
        raise LeagueNotFoundError(
            f"League with signup token '{signup_token}' not found"
        )
    return league


def create_team_and_assign_to_league(
    session: Session,
    team_name: str,
    password: str,
    league_id: int,
    school_name: str = "",
) -> Team:
    """Create a new team and directly assign it to a specific league"""
    # First get the league to retrieve institution_id
    league = session.get(League, league_id)
    if not league:
        raise LeagueNotFoundError(f"League with ID {league_id} not found")

    # Check if team name already exists
    existing_team = session.exec(select(Team).where(Team.name == team_name)).first()

    if existing_team:
        raise TeamError(f"Team with name '{team_name}' already exists")

    # Create the team with connection to both league and institution
    team = Team(
        name=team_name,
        school_name=school_name
        or team_name,  # Use provided school name or team name as fallback
        league_id=league_id,
        institution_id=league.institution_id,
        team_type=TeamType.STUDENT,
    )
    team.set_password(password)

    session.add(team)
    session.commit()
    session.refresh(team)

    return team


def get_result_by_publish_link(session: Session, publish_link: str) -> dict:
    """Get a published result by its publish link"""
    simulation = session.exec(
        select(SimulationResult)
        .where(SimulationResult.publish_link == publish_link)
        .where(SimulationResult.published == True)
    ).first()

    if not simulation:
        raise ValueError(f"Published result with link '{publish_link}' not found")

    # Get league for this simulation
    league = simulation.league

    # Process the simulation results
    result = process_simulation_results(simulation, league.name)

    return result
