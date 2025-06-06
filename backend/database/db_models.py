from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from passlib.context import CryptContext
from sqlalchemy import Column, DateTime, String, Text
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


class TeamType(str, PyEnum):
    STUDENT = "student"
    AGENT = "agent"


class LeagueType(str, PyEnum):
    STUDENT = "student"
    AGENT = "agent"
    INSTITUTION = "institution"  # Added new type


class Institution(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str = Field(unique=True, index=True)
    contact_person: str
    contact_email: str
    created_date: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    subscription_active: bool = Field(default=True)
    subscription_expiry: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    docker_access: bool = Field(default=False)
    password_hash: str
    teams: List["Team"] = Relationship(back_populates="institution")
    leagues: List["League"] = Relationship(back_populates="institution")

    def set_password(self, password: str):
        self.password_hash = get_password_hash(password)

    def verify_password(self, password: str):
        return verify_password(password, self.password_hash)


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
    name: str = Field(unique=True, index=True)
    school_name: str
    password_hash: str | None = None  # Optional for agent teams
    score: int = Field(default=0)
    color: str = Field(default="rgb(171,239,177)")
    league_id: int = Field(foreign_key="league.id")
    team_type: TeamType = Field(default=TeamType.STUDENT)
    is_demo: bool = Field(default=False)
    league: League = Relationship(back_populates="teams")
    submissions: List["Submission"] = Relationship(back_populates="team")
    api_key: Optional["AgentAPIKey"] = Relationship(
        back_populates="team",
        sa_relationship_kwargs={"uselist": False},
    )
    # New field for institution relationship
    institution_id: Optional[int] = Field(default=None, foreign_key="institution.id")
    institution: Optional["Institution"] = Relationship(back_populates="teams")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True))
    )

    __table_args__ = (UniqueConstraint("name", "league_id"),)

    def set_password(self, password: str):
        self.password_hash = get_password_hash(password)

    def verify_password(self, password: str):
        if not self.password_hash:  # Handle agent teams with no password
            return False
        return verify_password(password, self.password_hash)


class Submission(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    code: str = Field(sa_column=Column(Text()))  # Use Text for potentially long code
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    team_id: int = Field(default=None, foreign_key="team.id", nullable=True)
    team: Team = Relationship(back_populates="submissions")


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
    custom_rewards: str = Field(default="[10, 8, 6, 4, 3, 2, 1]")
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
        default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True))
    )
    last_used: datetime | None = None
    is_active: bool = Field(default=True)


class DemoUser(SQLModel, table=True):
    """Model for demo users with tracking information"""

    id: int = Field(primary_key=True, default=None)
    username: str = Field(index=True)  # Original username provided by user
    email: str | None = None  # Optional email provided by user
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
