from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, validator
from utils import get_games_names


class LeagueSignUp(BaseModel):
    """Model for creating a new league"""

    name: str
    game: str

    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("League name cannot be empty")
        return v.strip()

    @validator("game")
    def validate_game(cls, v):

        valid_games = get_games_names()
        if v not in valid_games:
            raise ValueError(f"Game must be one of: {', '.join(valid_games)}")
        return v


class TeamSignup(BaseModel):
    """Model for creating a new team"""

    name: str
    password: str
    school_name: Optional[str] = "Not Available"
    color: Optional[str] = "rgb(0,0,0)"
    score: Optional[int] = 0

    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Team name cannot be empty")
        return v.strip()


class SimulationConfig(BaseModel):
    """Model for simulation configuration"""
    num_simulations: int = Field(gt=0, le=10000)
    league_id: int
    league_name: Optional[str] = None  # For backwards compatibility
    game: Optional[str] = None
    custom_rewards: Optional[List[int]] = None
    use_docker: bool = True

    @validator("num_simulations")
    def validate_num_simulations(cls, v):
        if v > 10000:
            raise ValueError("Maximum number of simulations is 10000")
        return v


class LeagueName(BaseModel):
    """Model for specifying a league name"""

    name: str

    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("League name cannot be empty")
        return v.strip()


class TeamDelete(BaseModel):
    """Model for team deletion request"""

    name: str

    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Team name cannot be empty")
        return v.strip()


class LeagueResults(BaseModel):
    """Model for league results"""

    league_name: str
    id: int
    feedback: Union[str, dict, None] = None


class ExpiryDate(BaseModel):
    """Model for updating league expiry date"""

    date: datetime
    league: str

    @validator("league")
    def validate_league(cls, v):
        if not v.strip():
            raise ValueError("League name cannot be empty")
        return v.strip()

    @validator("date")
    def validate_date(cls, v):
        if v < datetime.now():
            raise ValueError("Expiry date cannot be in the past")
        return v


class SimulationResult(BaseModel):
    """Model for simulation results"""

    total_points: dict
    table: dict
    num_simulations: int
    timestamp: datetime
    feedback: Optional[Union[str, dict]] = None


class PublishRequest(BaseModel):
    """Model for publishing simulation results"""

    league_name: str
    simulation_id: int
    feedback: Optional[Union[str, dict]] = None
