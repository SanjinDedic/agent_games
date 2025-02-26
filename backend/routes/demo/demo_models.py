from pydantic import BaseModel, Field


class DemoLaunchRequest(BaseModel):
    """Model for demo mode launch request"""

    pass  # No specific fields needed for launch, just the endpoint call itself


class DemoGameSelectRequest(BaseModel):
    """Model for selecting a game in demo mode"""

    game_name: str = Field(..., description="Name of the game to try in demo mode")
