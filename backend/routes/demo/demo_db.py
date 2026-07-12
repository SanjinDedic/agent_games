import logging
import secrets
import string
from datetime import timedelta
from typing import List, Tuple

from sqlmodel import Session, delete, select

from backend.routes.auth.auth_config import DEMO_TOKEN_EXPIRY_MINUTES
from backend.database.db_models import (
    DemoUser,
    Institution,
    InstitutionSubscription,
    League,
    LeagueType,
    LeagueTutorial,
    Submission,
    SubmissionMetadata,
    Team,
    TeamType,
    Tutorial,
    get_password_hash,
)
from backend.database.submission_helpers import delete_submissions_for_teams
from backend.utils import get_games_names
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)


def get_or_create_demo_institution(session: Session) -> Institution:
    """Get or create the demo institution"""
    demo_institution = session.exec(
        select(Institution).where(Institution.name == "Demo Institution")
    ).first()

    if not demo_institution:
        # Create a default institution for demo entities
        now = utc_now()
        demo_institution = Institution(
            name="Demo Institution",
            contact_person="Demo Admin",
            contact_email="demo@example.com",
            created_date=now,
            password_hash=get_password_hash("demo_password"),
        )
        # Subscription state lives on the 1:1 record; assigning via the
        # relationship lets the cascade persist it with the institution.
        demo_institution.subscription = InstitutionSubscription(
            payment_method="admin",
            subscription_active=True,
            subscription_expiry=now + timedelta(days=365),
            created_date=now,
        )
        session.add(demo_institution)
        session.flush()  # Get the ID without committing the transaction

    return demo_institution


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

    # Find or create a demo institution
    demo_institution = get_or_create_demo_institution(session)

    # Create new demo user - using get_password_hash instead of set_password
    demo_user = Team(
        name=demo_username,
        school_name=username,
        team_type=TeamType.STUDENT,
        is_demo=True,
        league_id=unassigned_league.id,
        created_at=utc_now(),
        password_hash=get_password_hash(demo_password),
        institution_id=demo_institution.id,  # Use the real institution ID
    )

    session.add(demo_user)
    session.commit()
    session.refresh(demo_user)

    logger.info(f"Created demo user: {demo_username}")
    return demo_user


def save_demo_user_info(session: Session, username: str, email: str = None):
    """Save demo user information for tracking purposes"""
    demo_user_info = DemoUser(
        username=username, email=email, created_at=utc_now()
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

    # Find or create a demo institution
    demo_institution = get_or_create_demo_institution(session)

    # Create new demo league
    demo_league = League(
        name=league_name,
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game=game_name,
        league_type=LeagueType.STUDENT,
        is_demo=True,
        institution_id=demo_institution.id,
    )

    session.add(demo_league)
    session.flush()

    # Demo leagues showcase the platform, so they get every tutorial.
    for tutorial_id in session.exec(select(Tutorial.id)).all():
        session.add(
            LeagueTutorial(league_id=demo_league.id, tutorial_id=tutorial_id)
        )
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
    session: Session, age_minutes: int = DEMO_TOKEN_EXPIRY_MINUTES
):
    """Delete all submissions from demo users older than the specified age"""
    cutoff_time = utc_now() - timedelta(minutes=age_minutes)

    # Get all demo teams
    demo_teams = session.exec(select(Team).where(Team.is_demo == True)).all()

    if not demo_teams:
        logger.info("No demo teams found for cleanup")
        return 0

    demo_team_ids = [team.id for team in demo_teams]

    # Find old submission attempts from these teams
    old_meta = session.exec(
        select(SubmissionMetadata)
        .where(SubmissionMetadata.team_id.in_(demo_team_ids))
        .where(SubmissionMetadata.timestamp < cutoff_time)
    ).all()
    old_meta_ids = [m.id for m in old_meta]

    # Delete code rows first (they hold the FK), then the metadata
    if old_meta_ids:
        session.exec(delete(Submission).where(Submission.metadata_id.in_(old_meta_ids)))
        session.exec(
            delete(SubmissionMetadata).where(SubmissionMetadata.id.in_(old_meta_ids))
        )

    session.commit()
    count = len(old_meta_ids)
    logger.info(f"Cleaned up {count} old demo submissions")
    return count


def cleanup_expired_demo_users(session: Session, age_minutes: int = DEMO_TOKEN_EXPIRY_MINUTES):
    """Delete demo users older than the specified age"""
    cutoff_time = utc_now() - timedelta(minutes=age_minutes)

    # Find expired demo users
    expired_users = session.exec(
        select(Team).where(Team.is_demo == True).where(Team.created_at < cutoff_time)
    ).all()

    # Delete their submissions explicitly; deleting Team via the ORM would only
    # null out the metadata FK and strand orphaned rows
    delete_submissions_for_teams(session, [user.id for user in expired_users])

    # Delete expired users
    count = 0
    for user in expired_users:
        session.delete(user)
        count += 1

    session.commit()
    logger.info(f"Cleaned up {count} expired demo users")
    return count
