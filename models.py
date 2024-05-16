from pydantic import BaseModel, field_validator
from typing import List, Optional
from sqlmodel import Field, Session, SQLModel, create_engine, Relationship
from config import CURRENT_DB
from datetime import datetime
from auth import get_password_hash, verify_password

class AdminBase(SQLModel):
    username: str = Field(unique=True, index=True)
    password_hash: str

class Admin(AdminBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    def set_password(self, password: str):
        self.password_hash = get_password_hash(password)

    def verify_password(self, password: str):
        return verify_password(password, self.password_hash)

class LeagueBase(SQLModel):
    name: str = Field(unique=True, index=True)
    created_date: datetime
    expiry_date: datetime
    deleted_date: datetime | None = None
    active: bool
    signup_link: str | None = None

class League(LeagueBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    teams: List['Team'] = Relationship(back_populates='league')

class LeagueSignUp(SQLModel):
    name: str

class TeamBase(SQLModel):
    name: str = Field(index=True)
    school_name: str
    password_hash: str  # Change this field name to password_hash
    score: int = 0
    color: str = "rgb(171,239,177)"

class Team(TeamBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    league_id: int = Field(default=None, foreign_key="league.id")
    league: League = Relationship(back_populates='teams')
    submissions: List['Submission'] = Relationship(back_populates='team')

    def set_password(self, password: str):
        self.password_hash = get_password_hash(password)

    def verify_password(self, password: str):
        return verify_password(password, self.password_hash)

class SubmissionBase(SQLModel):
    code: str = Field(unique=True)
    timestamp: datetime 
    
class Submission(SubmissionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    team_id: int = Field(default=None, foreign_key='team.id')
    team: Team = Relationship(back_populates='submissions')
    

class TeamLogin(SQLModel):
    name: str
    password: str

    @field_validator('*')  # The '*' applies the validator to all fields
    def check_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError(f"{v} must not be empty or just whitespace.")
        return v

class TeamSignUp(SQLModel):
    name: str
    password: str
    school: str

    @field_validator('*')  # The '*' applies the validator to all fields
    def check_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError(f"{v} must not be empty or just whitespace.")
        return v
    
class CodeSubmit(SubmissionBase):
    pass

class AdminLogin(SQLModel):
    username: str
    password: str