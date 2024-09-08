from pydantic import BaseModel, field_validator, Field
from datetime import datetime
from typing import List, Optional

class TeamDelete(BaseModel):
    name: str

class LeagueName(BaseModel):
    name: str

class LeagueResults(BaseModel):
    league_name: str
    id: int

class LeagueAssignRequest(BaseModel):
    name: str

class SimulationConfig(BaseModel):
    num_simulations: int
    league_name: str
    custom_rewards: Optional[List[int]] = None
    use_docker: bool = True

class SimulationResult(BaseModel):
    results: dict

class LeagueSignUp(BaseModel):
    name: str
    game: str

class TeamSignup(BaseModel):
    name: str
    school_name: str = "Not Available"
    password: str
    score: int = 0
    color: str = "rgb(171,239,177)"

class TeamLogin(BaseModel):
    name: str
    password: str

    @field_validator('*')
    def check_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError(f"{v} must not be empty or just whitespace.")
        return v

class AdminLogin(BaseModel):
    username: str
    password: str

class SubmissionCode(BaseModel):
    code: str
    team_id: int = Field(default=None)
    league_id: int = Field(default=None)

class ResponseModel(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None

class ErrorResponseModel(BaseModel):
    status: str
    message: str

class ExpiryDate(BaseModel):
    date: datetime
    league: str

class GameName(BaseModel):
    game_name: str

    @field_validator('game_name')
    def game_name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Game name must not be empty or just whitespace')
        return v