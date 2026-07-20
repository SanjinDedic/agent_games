from pydantic import BaseModel, field_validator


class AdminLogin(BaseModel):
    """Admin login request model"""

    username: str
    password: str

    @field_validator("*")  # Add this validator
    def check_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError(f"{v} must not be empty or just whitespace.")
        return v


class TeamLogin(BaseModel):
    """Team login request model"""

    name: str
    password: str

    @field_validator("*")
    def check_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError(f"{v} must not be empty or just whitespace.")
        return v


class InstitutionLogin(BaseModel):
    """Institution login request model"""

    name: str
    password: str

    @field_validator("*")
    def check_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError(f"{v} must not be empty or just whitespace.")
        return v


class AgentLogin(BaseModel):
    """Agent login request model"""

    api_key: str

    @field_validator("api_key")
    def check_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError("API key must not be empty")
        return v


class TokenResponse(BaseModel):
    """Access token issued on a successful login."""

    access_token: str
    token_type: str = "bearer"


class CompetitionInfo(BaseModel):
    """One competition on the public login picker."""

    name: str
    icon: str | None = None


class CompetitionsResponse(BaseModel):
    """Public list of competitions for the login picker."""

    competitions: list[CompetitionInfo]
