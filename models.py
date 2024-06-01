from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict
from sqlmodel import Field, Session, SQLModel, create_engine, Relationship, UniqueConstraint
from config import CURRENT_DB
from datetime import datetime
from auth import get_password_hash, verify_password


class TeamDelete(SQLModel):
    name: str

class LeagueActive(SQLModel):
    name: str

class LeagueAssignRequest(SQLModel):
    name: str
    
class SimulationConfig(SQLModel):
    num_simulations: int
    league_name: str

class SimulationResult(SQLModel):
    results: dict

class LeagueSignUp(SQLModel):
    name: str
    game: str


class TeamSignup(SQLModel):
    name: str = Field(index=True)
    school_name: str
    password: str
    score: int = 0
    color: str = "rgb(171,239,177)"

    
class TeamLogin(SQLModel):
    name: str
    password: str

    @field_validator('*')
    def check_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError(f"{v} must not be empty or just whitespace.")
        return v

class TeamSignUp(SQLModel):
    name: str
    password: str
    school: str

    @field_validator('*')
    def check_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError(f"{v} must not be empty or just whitespace.")
        return v

class AdminLogin(SQLModel):
    username: str
    password: str

class SubmissionCode(SQLModel):
    code: str
    team_id: int = Field(default=None, foreign_key='team.id')
    league_id: int = Field(default=None, foreign_key='league.id')

#---------------------------------------------------------------------------------#
#---                                 TABLES                                    ---#
#---------------------------------------------------------------------------------#


class League(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    name: str = Field(unique=True, index=True)
    created_date: datetime
    expiry_date: datetime
    deleted_date: datetime | None = None
    active: bool
    signup_link: str | None = None
    folder: str | None = None
    teams: List['Team'] = Relationship(back_populates='league')
    game: str


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
    password_hash: str
    score: int = 0
    color: str = "rgb(171,239,177)"
    league_id: int = Field(default=None, foreign_key="league.id")
    league: League = Relationship(back_populates='teams')
    submissions: List['Submission'] = Relationship(back_populates='team')
    __table_args__ = (UniqueConstraint("name", "league_id"),)

    def set_password(self, password: str):
        self.password_hash = get_password_hash(password)

    def verify_password(self, password: str):
        return verify_password(password, self.password_hash)
    

class Submission(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    code: str
    timestamp: datetime
    team_id: int = Field(default=None, foreign_key='team.id')
    team: Team = Relationship(back_populates='submissions')