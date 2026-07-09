from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.schools.naming import sanitize_school_name
from backend.time_utils import interpret_as_sydney, utc_now
from backend.utils import get_games_names


class LeagueSignUp(BaseModel):
    """Model for creating a new league"""

    name: str
    game: str
    school_league: bool = False
    schools: List[str] = []
    sheet_url: Optional[str] = None

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

    @field_validator("schools")
    def dedupe_and_strip(cls, v):
        seen, out = set(), []
        for s in v:
            s2 = (s or "").strip()
            if not s2 or s2 in seen:
                continue
            if not sanitize_school_name(s2):
                raise ValueError(
                    f"School name '{s2}' must contain at least one alphanumeric character"
                )
            seen.add(s2)
            out.append(s2)
        return out

    @field_validator("sheet_url")
    def strip_sheet_url(cls, v):
        if v is None:
            return v
        v = v.strip()
        return v or None

    @model_validator(mode="after")
    def school_source_rules(self):
        if not self.school_league:
            return self
        has_static = bool(self.schools)
        has_sheet = bool(self.sheet_url)
        if has_static == has_sheet:
            raise ValueError(
                "A school league must have exactly one source: schools list OR sheet_url"
            )
        return self


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

    league_id: int
    id: int
    feedback: Union[str, dict, None] = None


class ExpiryDate(BaseModel):
    """Model for updating league expiry date"""

    date: datetime
    league_id: int

    @field_validator("date")
    def validate_date(cls, v):
        # Naive user-typed dates are read as Sydney wall time, stored as UTC
        v = interpret_as_sydney(v)

        if v < utc_now():
            raise ValueError("Expiry date cannot be in the past")
        return v


class TeamLeagueAssignment(BaseModel):
    """Model for assigning a team to a league"""
    
    team_id: int
    league_id: int

class LeagueName(BaseModel):
    """Model for specifying a league name (public lookup)."""

    name: str

    @field_validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("League name cannot be empty")
        return v.strip()


class LeagueIdRef(BaseModel):
    """Model for specifying a league by id (authenticated lookup)."""

    league_id: int


class TeamIdRef(BaseModel):
    """Model for specifying a team by id (authenticated lookup)."""

    team_id: int


class LeagueDelete(BaseModel):
    """Model for league deletion request"""

    league_id: int


class LeagueInfoUpdate(BaseModel):
    """Model for updating the per-league markdown info block."""

    league_id: int
    info_markdown: str = ""
