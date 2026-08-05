from pydantic import BaseModel


class ServiceStatus(BaseModel):
    """Model for service health status"""
    name: str
    status: str
    is_healthy: bool
