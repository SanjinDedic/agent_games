import logging
import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select

from backend.api import app
from backend.database.db_config import get_database_url
from backend.database.db_models import (
    UNASSIGNED_LEAGUE_NAME,
    League,
    LeagueType,
    Owner,
    Submission,
    SubmissionMetadata,
    Team,
    TeamType,
)
from backend.database.db_session import get_db
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now

# Precomputed bcrypt hashes to avoid expensive hashing on every test.
# Cost 4 (not the production 12) so login-flow checkpw is ~1ms instead of
# ~170ms; verify cost comes from the cost embedded in the hash itself.
_HASH_AA = "$2b$04$/.xNZ5ccGKIbRDAhGT3kBuDK/75Vl5viXLd/G5WCQRJPkqsorzdFm"  # "AA"
_HASH_BB = "$2b$04$abtlVrQQ6nJf6uWH7OF2IubTw2KzQtQPbBTMtfXZc290ek8jNv1Xi"  # "BB"
_HASH_CC = "$2b$04$0j273SvCCLMsx4mTO86gDeH4G812r/MXooXEyuyd7WwJk25Lj/wFG"  # "CC"
_HASH_TEST_PASSWORD = "$2b$04$S/gQ6t/Ex.ME3g76Ga09ne8sUTLDXpBbCy2iVj5RFBGlFXN9mH/o2"  # "test_password"
_HASH_TEAM_PASSWORD = "$2b$04$RqccKcL1cJP6rFjzclXWwOFgSQ2ALa/71UWz3O1GP9nyo60n9kPOi"  # "team_password"
_HASH_PASSWORD2 = "$2b$04$adNjLkXrrC9LgRXfZW1EjeYdj66q8jAGrgeJnJNF6KTPdxHb9Iw6W"  # "password2"

# Lookup for test files that need hashes for known passwords
TEST_PASSWORD_HASHES = {
    "AA": _HASH_AA,
    "BB": _HASH_BB,
    "CC": _HASH_CC,
    "test_password": _HASH_TEST_PASSWORD,
    "team_password": _HASH_TEAM_PASSWORD,
    "password2": _HASH_PASSWORD2,
    "expired_password": "$2b$04$LGfX.gdDyIfZvvtT8eq52eRCtl2JTIt3dXMQC6GllmCXXO/9fl7sS",
    "inactive_password": "$2b$04$X17RHyabQ7aKUwPP/9u98uOPKWjXhuW2wdZjg7SAwA7FQ8PrdUcBq",
}

# Set environment variables for testing before any imports
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_tests")
os.environ["DB_ENVIRONMENT"] = "test"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def celery_workers():
    """Fail fast with a clear message when the Celery workers are not up.

    Task-level tests enqueue to the real broker and need both queue workers
    running (docker compose starts them; test-runner depends_on their
    healthchecks).
    """
    from backend.tasks.celery_app import celery_app

    # limit=2 returns as soon as both workers reply (~10ms) instead of
    # waiting out the full broadcast timeout.
    replies = celery_app.control.inspect(timeout=5, limit=2).ping() or {}
    for prefix in ("validation", "simulation"):
        if not any(node.startswith(f"{prefix}@") for node in replies):
            pytest.fail(
                f"No {prefix} worker responded to ping — start the compose "
                f"workers first (docker compose up -d worker-validation "
                f"worker-simulation)"
            )
    return replies


_ENUM_TYPES = (
    "teamtype",
    "leaguetype",
)


@pytest.fixture(scope="session")
def db_engine():
    """Build schema once per test session; reuse across all tests.

    Per-test isolation is handled by TRUNCATE in db_session, not by
    dropping/recreating the schema. This avoids a PG ENUM duplicate-key race
    where SQLAlchemy create_all does not honor checkfirst for named types.
    """
    database_url = get_database_url()
    logger.info(f"Creating database engine: {database_url}")

    try:
        engine = create_engine(database_url)
        with engine.connect():
            pass
        logger.info("Test database already exists")
    except Exception as e:
        logger.info(f"Test database doesn't exist, creating it: {e}")
        base_url = database_url.rsplit("/", 1)[0] + "/postgres"
        maintenance_engine = create_engine(base_url)
        db_name = database_url.rsplit("/", 1)[1].split("?")[0]

        with maintenance_engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.execute(
                text(
                    f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
                )
            )
            conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
            conn.execute(text(f"CREATE DATABASE {db_name}"))

        maintenance_engine.dispose()
        logger.info("Test database created successfully")
        engine = create_engine(database_url)

    # Wipe any residual schema from a prior interrupted run, then build fresh.
    SQLModel.metadata.drop_all(engine)
    with engine.begin() as conn:
        for type_name in _ENUM_TYPES:
            conn.execute(text(f"DROP TYPE IF EXISTS {type_name} CASCADE"))
    SQLModel.metadata.create_all(engine)

    yield engine

    SQLModel.metadata.drop_all(engine)
    with engine.begin() as conn:
        for type_name in _ENUM_TYPES:
            conn.execute(text(f"DROP TYPE IF EXISTS {type_name} CASCADE"))
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Per-test session with truncated tables for isolation."""
    table_names = [t.name for t in SQLModel.metadata.sorted_tables]
    if table_names:
        quoted = ", ".join(f'"{name}"' for name in table_names)
        with db_engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))

    with Session(db_engine) as session:
        try:
            logger.debug(f"Test session using database: {db_engine.url}")
            yield session
            session.rollback()
        finally:
            session.close()


def populate_test_database(session):
    """Seed test database with precomputed hashes (no bcrypt cost).

    Deliberately seeds no Owner row: tests that need one mint a token via the
    owner_token fixture, and the setup-flow tests need a deployment that has not
    been claimed yet.
    """
    existing = session.exec(
        select(League).where(League.name == UNASSIGNED_LEAGUE_NAME)
    ).first()
    if existing:
        return

    now = utc_now()

    unassigned_league = League(
        name=UNASSIGNED_LEAGUE_NAME,
        created_date=now,
        expiry_date=now + timedelta(days=30),
        game="greedy_pig",
        league_type=LeagueType.STUDENT,
    )
    session.add(unassigned_league)

    for league_name, game in (
        ("greedy_pig_league", "greedy_pig"),
        ("prisoners_dilemma_league", "prisoners_dilemma"),
    ):
        session.add(
            League(
                name=league_name,
                created_date=now,
                expiry_date=now + timedelta(days=30),
                game=game,
                league_type=LeagueType.STUDENT,
            )
        )
    session.commit()
    session.refresh(unassigned_league)

    for name, school, pw_hash in [
        ("TeamA", "Sirius College", _HASH_AA),
        ("TeamB", "Sirius College", _HASH_BB),
        ("TeamC", "Glen Waverley Secondary College", _HASH_CC),
    ]:
        session.add(
            Team(
                name=name,
                school_name=school,
                password_hash=pw_hash,
                league_id=unassigned_league.id,
                team_type=TeamType.STUDENT,
            )
        )
    session.commit()


@pytest.fixture(autouse=True)
def init_test_db(db_session):
    """Seed fresh test data before each test"""
    populate_test_database(db_session)


@pytest.fixture
def client(db_session) -> TestClient:
    """Create TestClient with test database session"""
    def get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = get_test_db
    return TestClient(app)


@pytest.fixture
def owner_token(db_session: Session) -> str:
    """Create the deployment's owner account and return its token."""
    owner = Owner(username="test_owner", password_hash=_HASH_TEST_PASSWORD)
    db_session.add(owner)
    db_session.commit()

    return create_access_token(
        data={"sub": owner.username, "role": "owner"},
        expires_delta=timedelta(minutes=30),
    )


@pytest.fixture
def team_token(db_session):
    """Create test team with league assignment and return team token"""
    league = db_session.exec(select(League).where(League.name == "comp_test")).first()
    if not league:
        league = League(
            name="comp_test",
            created_date=utc_now(),
            expiry_date=utc_now() + timedelta(days=7),
            game="greedy_pig",
        )
        db_session.add(league)
        db_session.commit()
        db_session.refresh(league)

    team = Team(
        name="test_team",
        school_name="Test School",
        password_hash=_HASH_TEST_PASSWORD,
        league_id=league.id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    return make_student_token(team)


def make_student_token(team: Team, minutes: int = 30) -> str:
    """Build a student JWT for a persisted Team row (after db_session.refresh)."""
    return create_access_token(
        data={
            "sub": team.name,
            "role": "student",
            "team_id": team.id,
            "team_type": team.team_type.value,
            "league_id": team.league_id,
        },
        expires_delta=timedelta(minutes=minutes),
    )


def make_ai_agent_token(team: Team, minutes: int = 30) -> str:
    """Build an ai_agent JWT for a persisted Team row."""
    return create_access_token(
        data={
            "sub": team.name,
            "role": "ai_agent",
            "team_id": team.id,
            "team_type": team.team_type.value,
            "league_id": team.league_id,
        },
        expires_delta=timedelta(minutes=minutes),
    )


def add_submission(
    session,
    *,
    code: str,
    timestamp: datetime,
    team_id: int,
    league_id: int = None,
    duration_ms: float = None,
    hint_included: bool = False,
    ranking: int = None,
) -> Submission:
    """Create the metadata + code-row pair for a VALIDATED submission.

    Does not commit; save-update cascade inserts the metadata row with the code row.
    """
    meta = SubmissionMetadata(
        team_id=team_id,
        league_id=league_id,
        timestamp=timestamp,
        duration_ms=duration_ms,
        hint_included=hint_included,
    )
    sub = Submission(code=code, timestamp=timestamp, ranking=ranking, meta=meta)
    session.add(sub)
    return sub


def add_failed_submission(
    session,
    *,
    timestamp: datetime,
    team_id: int,
    league_id: int = None,
    duration_ms: float = None,
    hint_included: bool = False,
) -> SubmissionMetadata:
    """Create a metadata-only row for an attempt that failed validation."""
    meta = SubmissionMetadata(
        team_id=team_id,
        league_id=league_id,
        timestamp=timestamp,
        duration_ms=duration_ms,
        hint_included=hint_included,
    )
    session.add(meta)
    return meta


@pytest.fixture
def owner_headers(owner_token) -> dict:
    """Return headers with owner authentication"""
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture
def team_auth_headers(team_token) -> dict:
    """Return headers with team authentication"""
    return {"Authorization": f"Bearer {team_token}"}


@pytest.fixture
def test_league(db_session: Session) -> League:
    """Create a test league"""
    league = League(
        name="test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=1),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()
    return league


@pytest.fixture
def student_headers() -> dict:
    """Generic student-role bearer headers (no team_id). Suitable for tests that
    only check role-gating on owner-only endpoints."""
    token = create_access_token(
        data={"sub": "student", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def team_headers(db_session) -> dict:
    """TeamA seed-data bearer headers (role=student, includes team_id)."""
    team = db_session.exec(select(Team).where(Team.name == "TeamA")).first()
    return {"Authorization": f"Bearer {make_student_token(team)}"}
