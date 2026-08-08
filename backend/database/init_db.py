import logging
import os
import sys
import time
from datetime import timedelta

import psycopg
from sqlmodel import Session, SQLModel, select, text
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.database.db_config import get_database_url
from backend.database.db_models import (UNASSIGNED_LEAGUE_NAME, League,
                                        LeagueType, Team, TeamType,
                                        get_password_hash)
from backend.database.db_session import get_db_engine
from backend.time_utils import utc_now

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wait_for_postgres(max_retries=30, retry_interval=2):
    """Wait for PostgreSQL to be available"""
    database_url = get_database_url()
    sanitized_url = (
        database_url.rsplit("@", 1)[-1] if "@" in database_url else database_url
    )
    logger.info(f"Connecting to database (host info only): {sanitized_url}")

    retries = 0
    while retries < max_retries:
        try:
            engine = get_db_engine()
            with engine.connect():
                pass  # Test connection
            logger.info("Successfully connected to PostgreSQL")
            return True
        except Exception as e:
            logger.warning(f"Database connection attempt {retries+1} failed: {e}")
            retries += 1
            time.sleep(retry_interval)

    logger.error(f"Failed to connect to database after {max_retries} attempts")
    return False

# Arbitrary app-wide constant naming the "database init" advisory lock.
INIT_DB_ADVISORY_LOCK_KEY = 412_338_701


def initialize_database():
    """Initialize the PostgreSQL database for the first time"""
    logger.info("Initializing PostgreSQL database...")

    # Wait for PostgreSQL to be ready
    if not wait_for_postgres():
        logger.error("Could not connect to PostgreSQL, aborting initialization")
        return False

    # Create database engine
    engine = get_db_engine()

    # Several processes can attempt first-time init at once (e.g. two
    # containers booting against an empty database); serialize them so one
    # runs create_all/seed and the rest see the finished result. The lock is
    # session-scoped, so this connection must stay open for the duration.
    with engine.connect() as conn:
        conn.execute(
            text("SELECT pg_advisory_lock(:key)"), {"key": INIT_DB_ADVISORY_LOCK_KEY}
        )
        try:
            # Create all tables
            SQLModel.metadata.create_all(engine)

            # Populate with initial data (no-op if an admin already exists)
            populate_database(engine)
        finally:
            conn.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": INIT_DB_ADVISORY_LOCK_KEY},
            )

    logger.info("Database initialization complete")
    return True

def _seed_sample_data_enabled() -> bool:
    """Whether to seed the example leagues and TeamA/B/C.

    On for local dev and the manual test suite (docker-compose.yml sets it), off
    in production: a teacher's fresh install should not arrive holding three fake
    teams they have to find and delete.
    """
    return os.getenv("SEED_SAMPLE_DATA", "").strip().lower() in {"1", "true", "yes"}


def populate_database(engine):
    """Populate the database with the initial data the app cannot run without.

    No admin account is seeded — there is no default password to ship and forget
    to change. A fresh deployment is claimed through POST /auth/setup, which
    refuses once an admin exists.

    Idempotence is keyed on the 'unassigned' league rather than on an account,
    since that league is now the one row this function must always produce.
    """
    logger.info("Populating database with initial data...")

    with Session(engine) as session:
        existing = session.exec(
            select(League).where(League.name == UNASSIGNED_LEAGUE_NAME)
        ).first()
        if existing:
            logger.info("Database already seeded, skipping initial data population")
            return

        # The holding pen every team without a league sits in. Load-bearing:
        # team creation and league deletion both move teams here.
        unassigned_league = League(
            name=UNASSIGNED_LEAGUE_NAME,
            created_date=utc_now(),
            expiry_date=utc_now() + timedelta(days=365),
            game="greedy_pig",
            league_type=LeagueType.STUDENT,
        )
        session.add(unassigned_league)
        session.commit()
        session.refresh(unassigned_league)

        if not _seed_sample_data_enabled():
            logger.info("SEED_SAMPLE_DATA is off — seeded the unassigned league only")
            return

        for league_name, game in (
            ("greedy_pig_league", "greedy_pig"),
            ("prisoners_dilemma_league", "prisoners_dilemma"),
        ):
            session.add(
                League(
                    name=league_name,
                    created_date=utc_now(),
                    expiry_date=utc_now() + timedelta(days=30),
                    game=game,
                    league_type=LeagueType.STUDENT,
                )
            )
        session.commit()

        try:
            teams_data = {
                "teams": [
                    {
                        "name": "TeamA",
                        "password": os.getenv("TEAM_A_PASSWORD", "AA"),
                        "school": "Sirius College",
                    },
                    {
                        "name": "TeamB",
                        "password": os.getenv("TEAM_B_PASSWORD", "BB"),
                        "school": "Sirius College",
                    },
                    {
                        "name": "TeamC",
                        "password": os.getenv("TEAM_C_PASSWORD", "CC"),
                        "school": "Glen Waverley Secondary College",
                    },
                ]
            }

            teams_json_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "teams.json"
            )
            if os.path.exists(teams_json_path):
                import json

                with open(teams_json_path, "r") as f:
                    teams_data = json.load(f)

            for team_data in teams_data["teams"]:
                team = Team(
                    name=team_data["name"],
                    school_name=team_data["school"],
                    password_hash=get_password_hash(team_data["password"]),
                    league_id=unassigned_league.id,
                    team_type=TeamType.STUDENT,
                )
                session.add(team)

            session.commit()
            logger.info(f"Created {len(teams_data['teams'])} sample teams")
        except Exception as e:
            logger.error(f"Error creating sample teams: {e}")
            session.rollback()

        logger.info("Initial data population complete")


if __name__ == "__main__":
    # Non-zero exit on failure so container commands can gate server start
    # on successful init (see backend/Dockerfile CMD).
    raise SystemExit(0 if initialize_database() else 1)
