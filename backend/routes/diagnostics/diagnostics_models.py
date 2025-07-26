from enum import Enum as PyEnum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ServiceName(str, PyEnum):
    """Enum for service names"""

    VALIDATOR = "validator"
    SIMULATOR = "simulator"
    API = "api"

class LogsRequest(BaseModel):
    """Request model for getting service logs"""
    service: ServiceName
    tail: Optional[int] = Field(
        default=1000, description="Number of log lines to fetch (max 1000)"
    )

    @field_validator("tail")
    @classmethod
    def validate_tail(cls, v: Optional[int]) -> Optional[int]:
        if v and v > 1000:
            return 1000  # Cap at 1000 lines
        return v


class ServiceStatus(BaseModel):
    """Model for service health status"""
    name: str
    status: str
    is_healthy: bool
