from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ServiceName(str, Enum):
    """Enum for service names"""
    API = "api"
    VALIDATOR = "validator"
    SIMULATOR = "simulator"
    POSTGRES = "postgres"
    POSTGRES_TEST = "postgres_test"
    ALL = "all"


class LogsRequest(BaseModel):
    """Request model for getting service logs"""
    service: ServiceName = Field(default=ServiceName.ALL, description="Service name to get logs for")
    tail: Optional[int] = Field(default=100, description="Number of log lines to fetch")
    since: Optional[str] = Field(default=None, description="Only return logs since this timestamp (e.g. '2023-01-01T00:00:00Z')")


class ResourceUsage(BaseModel):
    """Model for resource usage of a Docker container"""
    container_id: str
    name: str
    cpu_percent: float
    memory_usage: str
    memory_percent: float
    network_io: Dict[str, str]
    disk_io: Dict[str, str]
    status: str
    uptime: str


class SystemResources(BaseModel):
    """Model for overall system resources"""
    cpu_percent: float
    memory_percent: float
    memory_available: str
    disk_percent: float
    disk_available: str
    load_average: List[float]


class DiagnosticsResponse(BaseModel):
    """Response model for diagnostics data"""
    containers: Dict[str, ResourceUsage]
    system: SystemResources


class ServiceStatus(BaseModel):
    """Model for service status"""
    name: str
    status: str
    health: str
    is_healthy: bool