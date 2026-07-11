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
from backend.database.db_models import (Admin, Institution,
                                        InstitutionSubscription, League,
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

def populate_database(engine):
    """Populate the database with initial data"""
    logger.info("Populating database with initial data...")

    with Session(engine) as session:
        # Check if admin already exists to prevent duplicates on rerun
        existing_admin = session.exec(select(Admin).where(Admin.username == "admin")).first()
        if existing_admin:
            logger.info("Admin already exists, skipping initial data population")
            return

        # Create administrator
        admin_password = os.getenv(
            "ADMIN_PASSWORD", "admin"
        )  # Default for backward compatibility
        admin = Admin(username="admin", password_hash=get_password_hash(admin_password))
        session.add(admin)

        # Create default institution
        institution_password = os.getenv(
            "INSTITUTION_PASSWORD", "institution"
        )  # Default for backward compatibility
        default_institution = Institution(
            name="Admin Institution",
            contact_person="Admin",
            contact_email="admin@admin.com",
            created_date=utc_now(),
            password_hash=get_password_hash(institution_password),
        )
        session.add(default_institution)
        session.flush()  # assign id before creating the subscription
        session.add(
            InstitutionSubscription(
                institution_id=default_institution.id,
                payment_method="admin",
                subscription_active=True,
                subscription_expiry=(utc_now() + timedelta(days=365)),
                created_date=utc_now(),
            )
        )
        session.commit()

        # Create unassigned league
        unassigned_league = League(
            name="unassigned",
            created_date=utc_now(),
            expiry_date=(
                utc_now() + timedelta(days=30)
            ),
            game="greedy_pig",
            league_type=LeagueType.STUDENT,
            institution_id=default_institution.id,
        )
        session.add(unassigned_league)

        # Create greedy pig league
        greedy_pig_league = League(
            name="greedy_pig_league",
            created_date=utc_now(),
            expiry_date=(
                utc_now() + timedelta(days=30)
            ),
            game="greedy_pig",
            league_type=LeagueType.STUDENT,
            institution_id=default_institution.id,
        )
        session.add(greedy_pig_league)

        # Create prisoners dilemma league
        prisoners_dilemma_league = League(
            name="prisoners_dilemma_league",
            created_date=utc_now(),
            expiry_date=(
                utc_now() + timedelta(days=30)
            ),
            game="prisoners_dilemma",
            league_type=LeagueType.STUDENT,
            institution_id=default_institution.id,
        )
        session.add(prisoners_dilemma_league)

        session.commit()

        # Create initial teams from teams.json
        try:
            # Define initial teams if teams.json isn't available
            teams_data = {
                "teams": [
                    {
                        "name": "TeamA",
                        "password": os.getenv(
                            "TEAM_A_PASSWORD", "AA"
                        ),  # Default for backward compatibility
                        "school": "Sirius College",
                    },
                    {
                        "name": "TeamB",
                        "password": os.getenv(
                            "TEAM_B_PASSWORD", "BB"
                        ),  # Default for backward compatibility
                        "school": "Sirius College",
                    },
                    {
                        "name": "TeamC",
                        "password": os.getenv(
                            "TEAM_C_PASSWORD", "CC"
                        ),  # Default for backward compatibility
                        "school": "Glen Waverley Secondary College",
                    },
                ]
            }

            # Try to open teams.json if available
            teams_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "teams.json")
            if os.path.exists(teams_json_path):
                import json
                with open(teams_json_path, "r") as f:
                    teams_data = json.load(f)

            # Create teams
            for team_data in teams_data["teams"]:
                team = Team(
                    name=team_data["name"],
                    school_name=team_data["school"],
                    password_hash=get_password_hash(team_data["password"]),
                    league_id=unassigned_league.id,
                    team_type=TeamType.STUDENT,
                    institution_id=default_institution.id,
                )
                session.add(team)

            session.commit()
            logger.info(f"Created {len(teams_data['teams'])} initial teams")
        except Exception as e:
            logger.error(f"Error creating initial teams: {e}")
            session.rollback()

        logger.info("Initial data population complete")

if __name__ == "__main__":
    # Non-zero exit on failure so container commands can gate server start
    # on successful init (see backend/Dockerfile CMD).
    raise SystemExit(0 if initialize_database() else 1)
