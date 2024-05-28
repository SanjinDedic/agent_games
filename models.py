from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict
from sqlmodel import Field, Session, SQLModel, create_engine, Relationship, UniqueConstraint
from config import CURRENT_DB
from datetime import datetime
from auth import get_password_hash, verify_password

class SimulationConfig(SQLModel):
    num_simulations: int
    league_name: str

class SimulationResult(SQLModel):
    results: dict

class LeagueSignUp(SQLModel):
    name: str
    game: str

class AdminBase(SQLModel):
    username: str = Field(unique=True, index=True)
    password_hash: str

class LeagueBase(SQLModel):
    name: str = Field(unique=True, index=True)
    created_date: datetime
    expiry_date: datetime
    deleted_date: datetime | None = None
    active: bool
    signup_link: str | None = None


class TeamBase(SQLModel):
    name: str = Field(index=True)
    school_name: str
    password_hash: str
    score: int = 0
    color: str = "rgb(171,239,177)"


class SubmissionBase(SQLModel):
    code: str = Field(unique=True)
    timestamp: datetime 
    
    
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

class League(LeagueBase, table=True):
    id: int = Field(primary_key=True, default=None)
    folder: str | None = None
    teams: List['Team'] = Relationship(back_populates='league')
    game: str


class Admin(AdminBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    def set_password(self, password: str):
        self.password_hash = get_password_hash(password)

    def verify_password(self, password: str):
        return verify_password(password, self.password_hash)
    

class Team(TeamBase, table=True):
    id: int = Field(primary_key=True)
    league_id: int = Field(default=None, foreign_key="league.id")
    league: League = Relationship(back_populates='teams')
    submissions: List['Submission'] = Relationship(back_populates='team')
    __table_args__ = (UniqueConstraint("name", "league_id"),)

    def set_password(self, password: str):
        self.password_hash = get_password_hash(password)

    def verify_password(self, password: str):
        return verify_password(password, self.password_hash)
    

class Submission(SubmissionBase, table=True):
    id: int = Field(primary_key=True, default=None)
    team_id: int = Field(default=None, foreign_key='team.id')
    team: Team = Relationship(back_populates='submissions')
    code: str