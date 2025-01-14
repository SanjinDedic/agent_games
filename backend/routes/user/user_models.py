from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SubmissionCode(BaseModel):
    """Model for code submissions from teams"""

    code: str
    team_id: int = Field(default=None)
    league_id: int = Field(default=None)


class LeagueAssignRequest(BaseModel):
    """Model for assigning teams to leagues"""

    name: str


class GameName(BaseModel):
    """Model for specifying game names"""

    game_name: str

    @field_validator("game_name")
    def validate_game_name(cls, v):
        if not v.strip():
            raise ValueError("Game name must not be empty")
        return v.strip()
