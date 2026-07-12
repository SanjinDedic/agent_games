from typing import Optional

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    """Model for service health status"""
    name: str
    status: str
    is_healthy: bool


class BenchmarkSubmission(BaseModel):
    """Payload for the load-test benchmark endpoint"""
    code: str
    game_name: str = "greedy_pig"
