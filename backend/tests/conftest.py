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
    Admin,
    DemoUser,
    Institution,
    InstitutionSubscription,
    League,
    LeagueType,
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
_HASH_ADMIN = "$2b$04$.WPpp.Mj.ExyhVOhCjTugOgLBq24T/4zTjrwvnGiOx4c6bFmAXHcG"  # "admin"
_HASH_INSTITUTION = "$2b$04$pvWMB/sRar78ntUsCb21lON3FpqsCypw8q.a.jVaEYzTu.e1mVEwq"  # "institution"
_HASH_AA = "$2b$04$/.xNZ5ccGKIbRDAhGT3kBuDK/75Vl5viXLd/G5WCQRJPkqsorzdFm"  # "AA"
_HASH_BB = "$2b$04$abtlVrQQ6nJf6uWH7OF2IubTw2KzQtQPbBTMtfXZc290ek8jNv1Xi"  # "BB"
_HASH_CC = "$2b$04$0j273SvCCLMsx4mTO86gDeH4G812r/MXooXEyuyd7WwJk25Lj/wFG"  # "CC"
_HASH_TEST_PASSWORD = "$2b$04$S/gQ6t/Ex.ME3g76Ga09ne8sUTLDXpBbCy2iVj5RFBGlFXN9mH/o2"  # "test_password"
_HASH_TEAM_PASSWORD = "$2b$04$RqccKcL1cJP6rFjzclXWwOFgSQ2ALa/71UWz3O1GP9nyo60n9kPOi"  # "team_password"
_HASH_PASSWORD2 = "$2b$04$adNjLkXrrC9LgRXfZW1EjeYdj66q8jAGrgeJnJNF6KTPdxHb9Iw6W"  # "password2"
_HASH_INST_PASSWORD = "$2b$04$mNAjfBlxpWDSuMxJR5.Ie.OesZS46hM0cEFivUPN3XjKMNSreOPEO"  # "inst_password"

# Lookup for test files that need hashes for known passwords
TEST_PASSWORD_HASHES = {
    "admin": _HASH_ADMIN,
    "institution": _HASH_INSTITUTION,
    "AA": _HASH_AA,
    "BB": _HASH_BB,
    "CC": _HASH_CC,
    "test_password": _HASH_TEST_PASSWORD,
    "team_password": _HASH_TEAM_PASSWORD,
    "password2": _HASH_PASSWORD2,
    "inst_password": _HASH_INST_PASSWORD,
    "expired_password": "$2b$04$LGfX.gdDyIfZvvtT8eq52eRCtl2JTIt3dXMQC6GllmCXXO/9fl7sS",
    "inactive_password": "$2b$04$X17RHyabQ7aKUwPP/9u98uOPKWjXhuW2wdZjg7SAwA7FQ8PrdUcBq",
}

# Set environment variables for testing before any imports
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_tests")
os.environ["DB_ENVIRONMENT"] = "test"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def build_institution(
    *,
    name,
    password_hash,
    contact_person="Test Contact",
    contact_email="test@example.com",
    created_date=None,
    subscription_active=True,
    subscription_expiry=None,
    docker_access=True,
    payment_method="admin",
    **extra,
):
    """Build an Institution with its 1:1 InstitutionSubscription attached via the
    relationship — NOT yet persisted.

    Subscription state (active/expiry) lives on InstitutionSubscription, so the
    inline subscription kwargs populate that record. Because the subscription is
    assigned through the relationship, a plain ``session.add(inst)`` +
    ``commit()``/``flush()`` cascades and persists it automatically — existing
    test code that adds/commits the institution itself keeps working unchanged.
    """
    now = created_date or utc_now()
    if subscription_expiry is None:
        subscription_expiry = now + timedelta(days=30)
    institution = Institution(
        name=name,
        contact_person=contact_person,
        contact_email=contact_email,
        created_date=now,
        docker_access=docker_access,
        password_hash=password_hash,
        **extra,
    )
    institution.subscription = InstitutionSubscription(
        payment_method=payment_method,
        subscription_active=subscription_active,
        subscription_expiry=subscription_expiry,
        created_date=now,
    )
    return institution


def create_test_institution(session, **kwargs):
    """build_institution + persist; returns the committed, refreshed Institution."""
    institution = build_institution(**kwargs)
    session.add(institution)
    session.commit()
    session.refresh(institution)
    return institution

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
    "supportticketcategory",
    "supportticketstatus",
    "supportticketsubmittertype",
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
        admin_engine = create_engine(base_url)
        db_name = database_url.rsplit("/", 1)[1].split("?")[0]

        with admin_engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.execute(
                text(
                    f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
                )
            )
            conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
            conn.execute(text(f"CREATE DATABASE {db_name}"))

        admin_engine.dispose()
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
    """Seed test database with precomputed hashes (no bcrypt cost)"""
    existing_admin = session.exec(select(Admin).where(Admin.username == "admin")).first()
    if existing_admin:
        return

    now = utc_now()

    admin = Admin(username="admin", password_hash=_HASH_ADMIN)
    session.add(admin)

    institution = create_test_institution(
        session,
        name="Admin Institution",
        contact_person="Admin",
        contact_email="admin@admin.com",
        created_date=now,
        subscription_expiry=now + timedelta(days=365),
        docker_access=True,
        password_hash=_HASH_INSTITUTION,
    )

    unassigned_league = League(
        name="unassigned",
        created_date=now,
        expiry_date=now + timedelta(days=30),
        game="greedy_pig",
        league_type=LeagueType.STUDENT,
        institution_id=institution.id,
    )
    session.add(unassigned_league)

    greedy_pig_league = League(
        name="greedy_pig_league",
        created_date=now,
        expiry_date=now + timedelta(days=30),
        game="greedy_pig",
        league_type=LeagueType.STUDENT,
        institution_id=institution.id,
    )
    session.add(greedy_pig_league)

    prisoners_dilemma_league = League(
        name="prisoners_dilemma_league",
        created_date=now,
        expiry_date=now + timedelta(days=30),
        game="prisoners_dilemma",
        league_type=LeagueType.STUDENT,
        institution_id=institution.id,
    )
    session.add(prisoners_dilemma_league)
    session.commit()

    for name, school, pw_hash in [
        ("TeamA", "Sirius College", _HASH_AA),
        ("TeamB", "Sirius College", _HASH_BB),
        ("TeamC", "Glen Waverley Secondary College", _HASH_CC),
    ]:
        session.add(Team(
            name=name,
            school_name=school,
            password_hash=pw_hash,
            league_id=unassigned_league.id,
            team_type=TeamType.STUDENT,
            institution_id=institution.id,
        ))
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
def admin_token(db_session: Session) -> str:
    """Create admin user and return admin token"""
    admin = Admin(
        username="test_admin", password_hash=_HASH_TEST_PASSWORD
    )
    db_session.add(admin)
    db_session.commit()

    return create_access_token(
        data={"sub": "admin", "role": "admin", "institution_id": 1},
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

    return create_access_token(
        data={
            "sub": team.name,
            "role": "student",
            "team_id": team.id,
            "team_type": team.team_type.value,
            "is_demo": team.is_demo,
            "institution_id": team.institution_id,
        },
        expires_delta=timedelta(minutes=30),
    )


def make_student_token(team: Team, minutes: int = 30) -> str:
    """Build a student JWT for a persisted Team row (after db_session.refresh)."""
    return create_access_token(
        data={
            "sub": team.name,
            "role": "student",
            "team_id": team.id,
            "team_type": team.team_type.value,
            "is_demo": team.is_demo,
            "institution_id": team.institution_id,
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
            "is_demo": team.is_demo,
            "institution_id": team.institution_id,
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
    sub = Submission(code=code, timestamp=timestamp, meta=meta)
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
def auth_headers(admin_token) -> dict:
    """Return headers with admin authentication"""
    return {"Authorization": f"Bearer {admin_token}"}


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
def setup_demo_data(db_session: Session) -> None:
    """Set up demo data in the test database"""
    # Get unassigned league
    unassigned = db_session.exec(
        select(League).where(League.name == "unassigned")
    ).first()

    # Create demo teams and tracking records
    for i in range(2):
        team_name = f"demo_team_{i}"
        team = db_session.exec(select(Team).where(Team.name == team_name)).first()

        if not team:
            # Create the Team with is_demo flag
            team = Team(
                name=team_name + "_demo",
                school_name=team_name,
                password_hash="test_hash",
                league_id=unassigned.id,
                is_demo=True,
                team_type=TeamType.STUDENT,
            )
            db_session.add(team)
            db_session.commit()
            db_session.refresh(team)

            # Create separate DemoUser tracking record
            demo_user = DemoUser(
                username=team_name,
                email=f"demo{i}@example.com",
                created_at=utc_now(),
            )
            db_session.add(demo_user)
            db_session.commit()

            # Add submissions for each team
            for j in range(3):
                add_submission(
                    db_session,
                    code=f"Demo code {j} for team {i}",
                    timestamp=utc_now() - timedelta(minutes=j),
                    team_id=team.id,
                )

    db_session.commit()


@pytest.fixture
def admin_headers(auth_headers) -> dict:
    """Alias for auth_headers — admin-role bearer headers."""
    return auth_headers


@pytest.fixture
def student_headers() -> dict:
    """Generic student-role bearer headers (no team_id). Suitable for tests that
    only check role-gating on admin-only endpoints."""
    token = create_access_token(
        data={"sub": "student", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def team_headers(db_session) -> dict:
    """TeamA seed-data bearer headers (role=student, includes team_id + institution_id)."""
    team = db_session.exec(select(Team).where(Team.name == "TeamA")).first()
    return {"Authorization": f"Bearer {make_student_token(team)}"}


@pytest.fixture
def institution_token(db_session: Session) -> str:
    """Create a fresh institution and return its institution-role JWT."""
    institution = create_test_institution(
        db_session,
        name="test_institution",
        contact_person="Test Person",
        contact_email="test@example.com",
        subscription_expiry=utc_now() + timedelta(days=30),
        docker_access=True,
        password_hash="test_hash",
    )

    return create_access_token(
        data={
            "sub": institution.name,
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(minutes=30),
    )


@pytest.fixture
def institution_headers(institution_token: str) -> dict:
    """Bearer headers wrapping institution_token."""
    return {"Authorization": f"Bearer {institution_token}"}
