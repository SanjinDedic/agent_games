import logging
import secrets
import string
from datetime import datetime, timedelta
from typing import List, Tuple

import pytz
from sqlmodel import Session, select

from backend.config import DEMO_TOKEN_EXPIRY
from backend.database.db_models import (
    DemoUser,
    League,
    LeagueType,
    Submission,
    Team,
    TeamType,
    get_password_hash,
)
from backend.utils import get_games_names

logger = logging.getLogger(__name__)
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


def generate_demo_password(length=12):
    """Generate a strong random password for demo users"""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_demo_user(
    session: Session, username: str, email: str = None
) -> Tuple[Team, str]:
    """Create a temporary demo user"""
    # Save user info to DemoUser table
    save_demo_user_info(session, username, email)

    # Create a unique username with suffix - truncate if too long
    # Ensure total length with suffix stays within 30 characters
    max_base_length = 30 - len("_Demo")
    truncated_username = username[:max_base_length]
    demo_username = f"{truncated_username}_Demo"
    demo_password = generate_demo_password()

    # Check if demo user already exists (shouldn't happen but just in case)
    existing_user = session.exec(select(Team).where(Team.name == demo_username)).first()

    if existing_user:
        # If it does exist, regenerate the password
        existing_user.password_hash = get_password_hash(demo_password)
        session.add(existing_user)
        session.commit()
        session.refresh(existing_user)
        return existing_user

    # Get unassigned league for initial placement
    unassigned_league = session.exec(
        select(League).where(League.name == "unassigned")
    ).first()

    if not unassigned_league:
        logger.error("Unassigned league not found")
        raise ValueError("Unassigned league not found")

    # Create new demo user - using get_password_hash instead of set_password
    demo_user = Team(
        name=demo_username,
        school_name=f"Demo User: {username}",
        team_type=TeamType.STUDENT,
        is_demo=True,
        league_id=unassigned_league.id,
        created_at=datetime.now(AUSTRALIA_SYDNEY_TZ),
        password_hash=get_password_hash(demo_password),
    )

    session.add(demo_user)
    session.commit()
    session.refresh(demo_user)

    logger.info(f"Created demo user: {demo_username}")
    return demo_user


def save_demo_user_info(session: Session, username: str, email: str = None):
    """Save demo user information for tracking purposes"""
    demo_user_info = DemoUser(
        username=username, email=email, created_at=datetime.now(AUSTRALIA_SYDNEY_TZ)
    )

    session.add(demo_user_info)
    session.commit()
    logger.info(f"Saved demo user info for: {username}, email: {email}")


def ensure_demo_leagues_exist(session: Session) -> List[League]:
    """Ensure demo leagues exist for all available games"""
    all_games = get_games_names()
    demo_leagues = []

    for game_name in all_games:
        demo_league = get_or_create_demo_league(session, game_name)
        demo_leagues.append(demo_league)

    return demo_leagues


def get_or_create_demo_league(session: Session, game_name: str) -> League:
    """Get an existing demo league or create a new one for the given game"""
    league_name = f"{game_name}_demo"

    # Check if league already exists
    existing_league = session.exec(
        select(League).where(League.name == league_name)
    ).first()

    if existing_league:
        return existing_league

    # Create new demo league
    demo_league = League(
        name=league_name,
        created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
        expiry_date=datetime.now(AUSTRALIA_SYDNEY_TZ)
        + timedelta(days=7),  # Longer than user expiry
        game=game_name,
        league_type=LeagueType.STUDENT,
        is_demo=True,
    )

    session.add(demo_league)
    session.commit()
    session.refresh(demo_league)

    logger.info(f"Created demo league: {league_name}")
    return demo_league


def assign_user_to_demo_league(session: Session, user_id: int, league_id: int) -> bool:
    """Assign a demo user to the demo league"""
    user = session.get(Team, user_id)
    if not user:
        logger.error(f"User with ID {user_id} not found")
        return False

    league = session.get(League, league_id)
    if not league:
        logger.error(f"League with ID {league_id} not found")
        return False

    user.league_id = league.id
    session.add(user)
    session.commit()

    logger.info(f"Assigned user {user.name} to league {league.name}")
    return True


def cleanup_old_demo_submissions(
    session: Session, age_minutes: int = DEMO_TOKEN_EXPIRY
):
    """Delete all submissions from demo users older than the specified age"""
    cutoff_time = datetime.now(AUSTRALIA_SYDNEY_TZ) - timedelta(minutes=age_minutes)

    # Get all demo teams
    demo_teams = session.exec(select(Team).where(Team.is_demo == True)).all()

    if not demo_teams:
        logger.info("No demo teams found for cleanup")
        return 0

    demo_team_ids = [team.id for team in demo_teams]

    # Find old submissions from these teams
    old_submissions = session.exec(
        select(Submission)
        .where(Submission.team_id.in_(demo_team_ids))
        .where(Submission.timestamp < cutoff_time)
    ).all()

    # Delete old submissions
    count = 0
    for submission in old_submissions:
        session.delete(submission)
        count += 1

    session.commit()
    logger.info(f"Cleaned up {count} old demo submissions")
    return count


def cleanup_expired_demo_users(session: Session, age_minutes: int = DEMO_TOKEN_EXPIRY):
    """Delete demo users older than the specified age"""
    cutoff_time = datetime.now(AUSTRALIA_SYDNEY_TZ) - timedelta(minutes=age_minutes)

    # Find expired demo users
    expired_users = session.exec(
        select(Team).where(Team.is_demo == True).where(Team.created_at < cutoff_time)
    ).all()

    # Delete expired users
    count = 0
    for user in expired_users:
        session.delete(user)
        count += 1

    session.commit()
    logger.info(f"Cleaned up {count} expired demo users")
    return count
