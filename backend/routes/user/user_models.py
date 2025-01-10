from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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
