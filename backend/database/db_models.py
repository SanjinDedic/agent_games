from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from passlib.context import CryptContext
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, UniqueConstraint

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


class League(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    name: str = Field(unique=True, index=True)
    created_date: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    expiry_date: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    deleted_date: datetime | None = None
    signup_link: str | None = None
    teams: List["Team"] = Relationship(back_populates="league")
    game: str
    league_type: LeagueType = Field(default=LeagueType.STUDENT)
    is_demo: bool = Field(default=False)  # Add this field
    simulation_results: List["SimulationResult"] = Relationship(back_populates="league")


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
    score: int = 0
    color: str = "rgb(171,239,177)"
    league_id: int = Field(foreign_key="league.id")
    team_type: TeamType = Field(default=TeamType.STUDENT)
    is_demo: bool = Field(default=False)  # Add this field
    league: League = Relationship(back_populates="teams")
    submissions: List["Submission"] = Relationship(back_populates="team")
    api_key: Optional["AgentAPIKey"] = Relationship(
        back_populates="team",
        sa_relationship_kwargs={"uselist": False},
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
    code: str
    timestamp: datetime
    team_id: int = Field(default=None, foreign_key="team.id", nullable=True)
    team: Team = Relationship(back_populates="submissions")


class SimulationResult(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    league_id: int = Field(foreign_key="league.id")
    league: League = Relationship(back_populates="simulation_results")
    timestamp: datetime
    simulation_results: List["SimulationResultItem"] = Relationship(
        back_populates="simulation_result"
    )
    published: bool = False
    num_simulations: int = 0
    custom_rewards: str = "[10, 8, 6, 4, 3, 2, 1]"
    feedback_str: str | None = None
    feedback_json: str | None = None


class SimulationResultItem(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    simulation_result_id: int = Field(foreign_key="simulationresult.id")
    simulation_result: SimulationResult = Relationship(
        back_populates="simulation_results"
    )
    team_id: int = Field(foreign_key="team.id")
    team: Team = Relationship()
    score: float = 0
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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: datetime | None = None
    is_active: bool = Field(default=True)
