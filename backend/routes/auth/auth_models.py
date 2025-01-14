from pydantic import BaseModel, field_validator


class AdminLogin(BaseModel):
    """Admin login request model"""

    username: str
    password: str


class TeamLogin(BaseModel):
    """Team login request model"""

    name: str
    password: str

    @field_validator("*")
    def check_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError(f"{v} must not be empty or just whitespace.")
        return v
