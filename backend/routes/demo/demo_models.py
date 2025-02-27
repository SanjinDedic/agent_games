import re

from pydantic import BaseModel, Field, field_validator


class DemoLaunchRequest(BaseModel):
    """Model for demo mode launch request"""

    pass  # No specific fields needed for launch, just the endpoint call itself


class DemoLaunchRequestWithUser(BaseModel):
    """Model for launching demo with user information"""

    username: str = Field(
        ..., description="Username for demo mode (max 10 chars, alphanumeric)"
    )
    email: str | None = Field(None, description="Optional email address")

    @field_validator("username")
    def validate_username(cls, v):
        # Check if username is empty
        if not v or not v.strip():
            raise ValueError("Username cannot be empty")

        # Check length
        if len(v) > 10:
            raise ValueError("Username must be 10 characters or less")

        # Check if alphanumeric
        if not re.match(r"^[a-zA-Z0-9]+$", v):
            raise ValueError("Username must contain only letters and numbers")

        return v.strip()

    @field_validator("email")
    def validate_email(cls, v):
        # Email is optional, but if provided, it should be valid
        if v is not None and v.strip():
            # Simple email regex
            if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
                raise ValueError("Please provide a valid email address")
            return v.strip()
        return None


class DemoGameSelectRequest(BaseModel):
    """Model for selecting a game in demo mode"""

    game_name: str = Field(..., description="Name of the game to try in demo mode")
