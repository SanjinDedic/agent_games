from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.utils import get_games_names


class CreateInstitution(BaseModel):
    """Model for creating a new institution"""

    name: str
    contact_person: str
    contact_email: EmailStr
    password: str
    subscription_expiry: datetime
    docker_access: bool = False

    @field_validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Institution name cannot be empty")
        return v.strip()


class InstitutionUpdate(BaseModel):
    """Model for updating an institution"""

    id: int
    name: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    subscription_active: Optional[bool] = None
    subscription_expiry: Optional[datetime] = None
    docker_access: Optional[bool] = None
    password: Optional[str] = None


class DeleteInstitution(BaseModel):
    """Model for deleting an institution"""

    id: int


class ToggleDockerAccess(BaseModel):
    """Model for toggling Docker access for an institution"""

    institution_id: int
    enable: bool


class CreateAgentTeam(BaseModel):
    """Model for creating an agent team"""

    name: str
    league_id: int

    @field_validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Team name cannot be empty")
        return v.strip()


class CreateAgentAPIKey(BaseModel):
    """Model for creating an API key"""

    team_id: int
