from pydantic import BaseModel
from typing import List, Optional
from sqlmodel import Field, Session, SQLModel, create_engine, Relationship
from config import CURRENT_DB
from datetime import datetime


class Admin(BaseModel):
    password: str
    

class League(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True,index=True)
    expiry_date: datetime
    
    teams: List['Team'] = Relationship(back_populates='league')


class TeamBase(SQLModel):
    name: str = Field(index=True)
    school_name: str
    password: str
    score: int = 0
    color: str = "rgb(171,239,177)"

class Team(TeamBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    league_id: int = Field(default=None, foreign_key="league.id")
    league: League = Relationship(back_populates='team')
    submissions: List['Submission'] = Relationship(back_populates='team')

class SubmissionBase(SQLModel):
    code: str = Field(unique=True)
    timestamp: datetime 
    
class Submission(SubmissionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    team_id: int = Field(default=None, foreign_key='team.id')
    team: Team = Relationship(back_populates='submission')
    

class TeamLogin(TeamBase):
    pass
    
class CodeSubmit(SubmissionBase):
    pass

class AdminLogin(SQLModel):
    password: str