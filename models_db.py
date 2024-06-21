from typing import List, Optional, Dict
from sqlmodel import Field, SQLModel,  Relationship, UniqueConstraint, DateTime, Column
from config import CURRENT_DB
from datetime import datetime
from auth import get_password_hash, verify_password




#---------------------------------------------------------------------------------#
#---                                 TABLES                                    ---#
#---------------------------------------------------------------------------------#


class League(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    name: str = Field(unique=True, index=True)
    created_date: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    expiry_date: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    deleted_date: datetime | None = None
    signup_link: str | None = None
    folder: str | None = None
    teams: List['Team'] = Relationship(back_populates='league')
    game: str
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
    team_id: int = Field(default=None, foreign_key='team.id', nullable=True)
    team: Team = Relationship(back_populates='submissions')


class SimulationResult(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    league_id: int = Field(foreign_key="league.id")
    league: League = Relationship(back_populates="simulation_results")
    timestamp: datetime
    simulation_results: List["SimulationResultItem"] = Relationship(back_populates="simulation_result")
    published: bool = False # this needs to be restricted to only one result per league
    num_simulations: int = 0 #has to be there


class SimulationResultItem(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    simulation_result_id: int = Field(foreign_key="simulationresult.id")
    simulation_result: SimulationResult = Relationship(back_populates="simulation_results")
    team_id: int = Field(foreign_key="team.id")
    team: Team = Relationship()
    score: int = 0
    wins: int = 0