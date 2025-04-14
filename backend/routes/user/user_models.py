from pydantic import BaseModel, Field, field_validator


class SubmissionCode(BaseModel):
    """Model for code submissions from teams"""

    code: str
    team_id: int = Field(default=None)
    league_id: int = Field(default=None)


class LeagueAssignRequest(BaseModel):
    """Model for assigning teams to leagues"""

    name: str

    @field_validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("League name cannot be empty")
        return v.strip()


class GameName(BaseModel):
    """Model for specifying game names"""

    game_name: str

    @field_validator("game_name")
    def validate_game_name(cls, v):
        if not v.strip():
            raise ValueError("Game name must not be empty")
        return v.strip()


class DirectLeagueSignup(BaseModel):
    """Model for direct team signup with league token"""

    team_name: str
    password: str
    signup_token: str
    school_name: str = ""  # Add school_name field with default empty string

    @field_validator("team_name", "password")
    def validate_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()
