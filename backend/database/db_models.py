import os
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

import bcrypt as _bcrypt
from sqlalchemy import JSON, Column, DateTime, String, Text
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from backend.time_utils import utc_now

# Test runs set BCRYPT_ROUNDS=4 so runtime hashing costs ~1ms instead of ~170ms.
_BCRYPT_ROUNDS = int(os.environ.get("BCRYPT_ROUNDS", "12"))


def get_password_hash(password):
    if isinstance(password, str):
        password = password.encode("utf-8")
    return _bcrypt.hashpw(password, _bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain_password, hashed_password):
    if isinstance(plain_password, str):
        plain_password = plain_password.encode("utf-8")
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode("utf-8")
    return _bcrypt.checkpw(plain_password, hashed_password)


class TeamType(str, PyEnum):
    STUDENT = "student"
    AGENT = "agent"


class LeagueType(str, PyEnum):
    STUDENT = "student"
    AGENT = "agent"
    INSTITUTION = "institution"  # Added new type


class Institution(SQLModel, table=True):
    """Operational identity of an institution: who logs in and what they own.

    All subscription/billing/Stripe state lives in the 1:1 InstitutionSubscription
    record (see `subscription`), keeping this table free of payment concerns.
    """

    id: int = Field(primary_key=True)
    name: str = Field(unique=True, index=True)
    contact_person: str
    contact_email: str
    address: Optional[str] = None
    created_date: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    password_hash: str
    teams: List["Team"] = Relationship(back_populates="institution")
    leagues: List["League"] = Relationship(back_populates="institution")
    subscription: Optional["InstitutionSubscription"] = Relationship(
        back_populates="institution",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )

    def set_password(self, password: str):
        self.password_hash = get_password_hash(password)

    def verify_password(self, password: str):
        return verify_password(password, self.password_hash)


class InstitutionSubscription(SQLModel, table=True):
    """All subscription, billing, and Stripe-linkage state for one Institution.

    One row per institution (1:1). It owns:
      - the access window (subscription_active / subscription_expiry) read by the
        login gate,
      - how access was obtained and billed (payment_method / tier / auto_renew),
      - the Stripe object IDs webhooks use to tie renewals and cancellations back
        to the institution (the checkout session ID is unique: one paid session
        creates exactly one institution — a replay/reuse guard),
      - and, for the invoiced plan only, the business billing contact (who pays
        the invoice), kept distinct from the institution's teaching/login contact
        which lives on Institution.
    """

    __tablename__ = "institution_subscription"

    id: Optional[int] = Field(default=None, primary_key=True)
    institution_id: int = Field(
        foreign_key="institution.id", unique=True, index=True
    )
    # "card" (Stripe Checkout), "invoice" (Stripe send_invoice), or "admin"
    # (manually granted, no Stripe).
    payment_method: str = Field(default="admin")
    tier: Optional[str] = None
    subscription_active: bool = Field(default=True)
    subscription_expiry: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    auto_renew: bool = Field(default=False)
    stripe_customer_id: Optional[str] = Field(default=None, index=True)
    stripe_subscription_id: Optional[str] = Field(default=None, index=True)
    stripe_checkout_session_id: Optional[str] = Field(
        default=None, unique=True, index=True
    )
    stripe_invoice_id: Optional[str] = Field(default=None, index=True)
    business_contact_name: Optional[str] = None
    business_contact_email: Optional[str] = None
    created_date: datetime = Field(sa_column=Column(DateTime(timezone=True)))

    institution: Optional["Institution"] = Relationship(back_populates="subscription")


class League(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    name: str = Field(index=True)  # Remove unique=True from here
    created_date: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    expiry_date: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    deleted_date: datetime | None = None
    signup_link: str | None = None
    teams: List["Team"] = Relationship(back_populates="league")
    game: str
    league_type: LeagueType = Field(default=LeagueType.STUDENT)
    is_demo: bool = Field(default=False)
    school_league: bool = Field(default=False)
    schools_config: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    info_markdown: str = Field(default="", sa_column=Column(Text(), nullable=False, server_default=""))
    simulation_results: List["SimulationResult"] = Relationship(back_populates="league")
    # New field for institution relationship
    institution_id: Optional[int] = Field(default=None, foreign_key="institution.id")
    institution: Optional["Institution"] = Relationship(back_populates="leagues")

    # Add a table-level unique constraint for name + institution_id
    __table_args__ = (UniqueConstraint("name", "institution_id"),)


class Admin(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str

    def set_password(self, password: str):
        self.password_hash = get_password_hash(password)

    def verify_password(self, password: str):
        return verify_password(password, self.password_hash)


class Team(SQLModel, table=True):
    id: int = Field(primary_key=True)
    # Not globally unique: names are scoped per-institution by the composite
    # constraints below, so different institutions can reuse a name like
    # "Team A". A name is the team's stable identity within its institution as
    # it moves between leagues. The index stays for name lookups (login,
    # simulation attribution).
    name: str = Field(index=True)
    school_name: str
    password_hash: str | None = None  # Optional for agent teams
    score: int = Field(default=0)
    color: str = Field(default="rgb(171,239,177)")
    league_id: int = Field(foreign_key="league.id")
    team_type: TeamType = Field(default=TeamType.STUDENT)
    is_demo: bool = Field(default=False)
    league: League = Relationship(back_populates="teams")
    submission_attempts: List["SubmissionMetadata"] = Relationship(back_populates="team")
    api_key: Optional["AgentAPIKey"] = Relationship(
        back_populates="team",
        sa_relationship_kwargs={"uselist": False},
    )
    # New field for institution relationship
    institution_id: Optional[int] = Field(default=None, foreign_key="institution.id")
    institution: Optional["Institution"] = Relationship(back_populates="teams")
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True))
    )

    # Primary rule: a team name is unique within an institution. The
    # (name, league_id) constraint is a secondary guard for teams whose league
    # has no institution (institution_id NULL) — Postgres treats NULLs as
    # distinct in a unique constraint, so the institution rule can't cover them.
    __table_args__ = (
        UniqueConstraint("name", "institution_id"),
        UniqueConstraint("name", "league_id"),
    )

    def set_password(self, password: str):
        self.password_hash = get_password_hash(password)

    def verify_password(self, password: str):
        if not self.password_hash:  # Handle agent teams with no password
            return False
        return verify_password(password, self.password_hash)


class SubmissionMetadata(SQLModel, table=True):
    """One row per submission attempt, pass or fail. Drives rate limiting
    and hint availability. A linked Submission row == passed validation."""

    id: Optional[int] = Field(default=None, primary_key=True)
    # nullable: cleanup_expired_demo_users deletes Teams via the ORM, which nulls child FKs
    team_id: Optional[int] = Field(
        default=None, foreign_key="team.id", nullable=True, index=True
    )
    league_id: Optional[int] = Field(default=None, foreign_key="league.id", nullable=True)
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    duration_ms: Optional[float] = Field(default=None)
    hint_included: bool = Field(default=False)
    team: Optional[Team] = Relationship(back_populates="submission_attempts")
    submission: Optional["Submission"] = Relationship(
        back_populates="meta",
        sa_relationship_kwargs={"uselist": False},
    )


class Submission(SQLModel, table=True):
    """Validated code only. 1:1 with SubmissionMetadata via unique FK."""

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(sa_column=Column(Text()))  # Use Text for potentially long code
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    # Rank against the game's validation bots (1 = best, competition ranking),
    # from the validation run's total_points. Not a league standing.
    ranking: Optional[int] = Field(default=None)
    metadata_id: int = Field(foreign_key="submissionmetadata.id", unique=True, index=True)
    # `metadata` is reserved on SQLAlchemy declarative classes
    meta: SubmissionMetadata = Relationship(back_populates="submission")

# In backend/database/db_models.py

class SimulationResult(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    league_id: int = Field(foreign_key="league.id")
    league: League = Relationship(back_populates="simulation_results")
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    simulation_results: List["SimulationResultItem"] = Relationship(
        back_populates="simulation_result"
    )
    published: bool = Field(default=False)
    num_simulations: int = Field(default=0)
    custom_rewards: str = Field(default="[10, 0, 0, 0, 0, 0, 0]")
    feedback_str: str | None = Field(default=None, sa_column=Column(Text()))
    feedback_json: str | None = Field(default=None, sa_column=Column(Text()))
    publish_link: str | None = Field(default=None)  # New field for the publish link


class SimulationResultItem(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    simulation_result_id: int = Field(foreign_key="simulationresult.id")
    simulation_result: SimulationResult = Relationship(
        back_populates="simulation_results"
    )
    team_id: int = Field(foreign_key="team.id")
    team: Team = Relationship()
    score: float = Field(default=0)
    custom_value1: float | None = None
    custom_value2: float | None = None
    custom_value3: float | None = None
    custom_value1_name: str | None = None
    custom_value2_name: str | None = None
    custom_value3_name: str | None = None


class AgentAPIKey(SQLModel, table=True):
    """Model for API key management"""

    id: int = Field(primary_key=True, default=None)
    key: str = Field(unique=True, index=True)
    team_id: int = Field(
        foreign_key="team.id", unique=True
    )  # Ensures one API key per team
    team: Team = Relationship(back_populates="api_key")
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True))
    )
    last_used: datetime | None = None
    is_active: bool = Field(default=True)


class AIProviderKey(SQLModel, table=True):
    """Stores API keys for external AI providers (OpenAI, etc.)"""

    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str = Field(unique=True, index=True)  # e.g. "openai"
    api_key: str = Field(sa_column=Column(Text()))
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True))
    )


class DemoUser(SQLModel, table=True):
    """Model for demo users with tracking information"""

    id: int = Field(primary_key=True, default=None)
    username: str = Field(index=True)  # Original username provided by user
    email: str | None = None  # Optional email provided by user
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))


class SupportTicketCategory(str, PyEnum):
    BUG = "bug"
    SUPPORT = "support"
    FEEDBACK = "feedback"


class SupportTicketStatus(str, PyEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class SupportTicketSubmitterType(str, PyEnum):
    TEAM = "team"
    INSTITUTION = "institution"


class SupportTicket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category: SupportTicketCategory
    subject: str
    description: str = Field(sa_column=Column(Text()))
    status: SupportTicketStatus = Field(default=SupportTicketStatus.OPEN, index=True)
    admin_note: Optional[str] = Field(default=None, sa_column=Column(Text()))
    submitter_type: SupportTicketSubmitterType = Field(index=True)
    team_id: Optional[int] = Field(default=None, foreign_key="team.id", index=True)
    institution_id: Optional[int] = Field(
        default=None, foreign_key="institution.id", index=True
    )
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True))
    )

    team: Optional["Team"] = Relationship()
    institution: Optional["Institution"] = Relationship()
    attachments: List["SupportTicketAttachment"] = Relationship(
        back_populates="ticket",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class SupportTicketAttachment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="supportticket.id", index=True)
    s3_key: str
    content_type: str
    size_bytes: int
    original_filename: str
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True))
    )

    ticket: SupportTicket = Relationship(back_populates="attachments")


class Tutorial(SQLModel, table=True):
    """An ordered collection of exercises preparing students for agent games."""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(unique=True, index=True)
    description: str = Field(default="", sa_column=Column(Text(), nullable=False))
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True))
    )

    exercises: List["Exercise"] = Relationship(
        back_populates="tutorial",
        sa_relationship_kwargs={
            "order_by": "Exercise.order_index",
            "cascade": "all, delete-orphan",
        },
    )


class LeagueTutorial(SQLModel, table=True):
    """Attaches a tutorial to a league (many-to-many).

    A league has 0..many tutorials; teams only see the tutorials attached to
    their league. Tutorials are a global content library, so the same tutorial
    can be attached to any number of leagues without duplicating content.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    league_id: int = Field(foreign_key="league.id", index=True)
    tutorial_id: int = Field(foreign_key="tutorial.id", index=True)

    __table_args__ = (UniqueConstraint("league_id", "tutorial_id"),)


class Exercise(SQLModel, table=True):
    """One coding problem inside a tutorial.

    Tests live in `test_code`: an admin-trusted Python test script
    (backend/exercise_worker/tasks.py) exec'd into the same namespace as
    the student's code. It can test multiple functions and check print
    output. Authored by the seed script or through the admin exercise
    editor; students never see it. `entry_function` still names the one
    function every submission must define, so a wrong-name submission fails
    fast with a clear message. `solution` is an optional reference solution
    for the admin editor's Run workflow — like test_code, it never reaches
    students. `exercise_hints` is an ordered list of Markdown strings shown
    to students separately from the problem text.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    tutorial_id: int = Field(foreign_key="tutorial.id", index=True)
    order_index: int = Field(default=0)
    title: str
    problem_markdown: str = Field(sa_column=Column(Text(), nullable=False))
    starter_code: str = Field(default="", sa_column=Column(Text(), nullable=False))
    entry_function: str
    test_code: Optional[str] = Field(
        default=None, sa_column=Column(Text(), nullable=True)
    )
    solution: Optional[str] = Field(
        default=None, sa_column=Column(Text(), nullable=True)
    )
    exercise_hints: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True))
    )

    tutorial: Tutorial = Relationship(back_populates="exercises")


class ExerciseSubmissionMetadata(SQLModel, table=True):
    """One row per exercise submission attempt, pass or fail. Drives rate
    limiting. A linked ExerciseSubmission row == the code was safe and ran."""

    id: Optional[int] = Field(default=None, primary_key=True)
    # nullable: cleanup_expired_demo_users deletes Teams via the ORM, which nulls child FKs
    team_id: Optional[int] = Field(
        default=None, foreign_key="team.id", nullable=True, index=True
    )
    exercise_id: int = Field(foreign_key="exercise.id", index=True)
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    duration_ms: Optional[float] = Field(default=None)

    team: Optional[Team] = Relationship()
    exercise: Exercise = Relationship()
    submission: Optional["ExerciseSubmission"] = Relationship(
        back_populates="meta",
        sa_relationship_kwargs={"uselist": False},
    )


class ExerciseSubmission(SQLModel, table=True):
    """Code that was safe and executed (its tests may still fail). 1:1 with
    ExerciseSubmissionMetadata via unique FK. `passed` == every test passed;
    `test_results` holds the per-test outcomes shown to the student."""

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(sa_column=Column(Text()))
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    passed: bool = Field(default=False)
    test_results: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    metadata_id: int = Field(
        foreign_key="exercisesubmissionmetadata.id", unique=True, index=True
    )
    # `metadata` is reserved on SQLAlchemy declarative classes
    meta: ExerciseSubmissionMetadata = Relationship(back_populates="submission")
