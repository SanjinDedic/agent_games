from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from backend.utils import get_games_names


class LeagueSignUp(BaseModel):
    """Model for creating a new league"""

    name: str
    game: str

    @field_validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("League name cannot be empty")
        return v.strip()

    @field_validator("game")
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

    @field_validator("name")
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

    @field_validator("num_simulations")
    def validate_num_simulations(cls, v):
        if v < 1 or v > 20000:
            raise ValueError("Simulations must be between 1 and 20000")
        return v


class TeamDelete(BaseModel):
    """Model for team deletion request"""

    id: int


class LeagueResults(BaseModel):
    """Model for league results"""

    league_name: str
    id: int
    feedback: Union[str, dict, None] = None


class ExpiryDate(BaseModel):
    """Model for updating league expiry date"""

    date: datetime
    league: str

    @field_validator("league")
    def validate_league(cls, v):
        if not v.strip():
            raise ValueError("League name cannot be empty")
        return v.strip()

    @field_validator("date")
    def validate_date(cls, v):
        if v < datetime.now():
            raise ValueError("Expiry date cannot be in the past")
        return v


class TeamLeagueAssignment(BaseModel):
    """Model for assigning a team to a league"""
    
    team_id: int
    league_id: int

class LeagueName(BaseModel):
    """Model for specifying a league name"""

    name: str

    @field_validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("League name cannot be empty")
        return v.strip()


class LeagueDelete(BaseModel):
    """Model for league deletion request"""

    name: str

    @field_validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("League name cannot be empty")
        return v.strip()
