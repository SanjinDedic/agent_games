import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlmodel import Session

from backend.routes.diagnostics.diagnostics_router import get_resource_stats
from backend.routes.diagnostics.diagnostics_models import ServiceName
from backend.models_api import ErrorResponseModel, ResponseModel


@pytest.mark.asyncio
async def test_resource_stats_success_all_services():
    """Test successful retrieval of resource stats for all services."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock resource usage data for all services
    mock_service_usage = {
        "service1": {
            "container_id": "container123",
            "name": "service1",
            "status": "running",
            "cpu_percent": 15.0,
            "memory_usage": "200MB",
            "memory_percent": 12.5,
            "network_io": {"rx": "10MB", "tx": "5MB"},
            "disk_io": {"read": "50MB", "write": "20MB"},
            "uptime": "3d 4h"
        },
        "service2": {
            "container_id": "container456",
            "name": "service2",
            "status": "running",
            "cpu_percent": 8.0,
            "memory_usage": "150MB",
            "memory_percent": 9.5,
            "network_io": {"rx": "8MB", "tx": "3MB"},
            "disk_io": {"read": "30MB", "write": "15MB"},
            "uptime": "2d 12h"
        }
    }
    
    # Create mock for get_all_services_resource_usage
    mock_get_all_services_resource_usage = MagicMock(return_value=mock_service_usage)
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_all_services_resource_usage", mock_get_all_services_resource_usage):
        
        response = await get_resource_stats(service=ServiceName.ALL, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ResponseModel)
        assert response.status == "success"
        assert "resources" in response.data
        assert mock_get_all_services_resource_usage.called


@pytest.mark.asyncio
async def test_resource_stats_success_single_service():
    """Test successful retrieval of resource stats for a single service."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock resource usage data for a single service
    mock_service_usage = {
        "container_id": "container123",
        "name": "api",
        "status": "running",
        "cpu_percent": 15.0,
        "memory_usage": "200MB",
        "memory_percent": 12.5,
        "network_io": {"rx": "10MB", "tx": "5MB"},
        "disk_io": {"read": "50MB", "write": "20MB"},
        "uptime": "3d 4h"
    }
    
    # Create mock for get_service_resource_usage
    mock_get_service_resource_usage = MagicMock(return_value=mock_service_usage)
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_service_resource_usage", mock_get_service_resource_usage):
        
        response = await get_resource_stats(service=ServiceName.API, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ResponseModel)
        assert response.status == "success"
        assert "resources" in response.data
        assert mock_get_service_resource_usage.called
        mock_get_service_resource_usage.assert_called_with(ServiceName.API.value)


@pytest.mark.asyncio
async def test_resource_stats_no_access():
    """Test resource stats retrieval with no Docker access."""
    # Mock dependencies
    mock_user = {"role": "institution", "institution_id": 1}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return False
    mock_check_docker_access = AsyncMock(return_value=False)
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access):
        response = await get_resource_stats(service=ServiceName.ALL, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ErrorResponseModel)
        assert response.status == "error"
        assert "access" in response.message.lower()


@pytest.mark.asyncio
async def test_resource_stats_exception_all_services():
    """Test handling of exceptions during resource stats retrieval for all services."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock get_all_services_resource_usage to raise an exception
    mock_get_all_services_resource_usage = MagicMock(side_effect=Exception("Test exception"))
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_all_services_resource_usage", mock_get_all_services_resource_usage):
        
        response = await get_resource_stats(service=ServiceName.ALL, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ErrorResponseModel)
        assert response.status == "error"
        assert "failed to retrieve resource stats" in response.message.lower()


@pytest.mark.asyncio
async def test_resource_stats_exception_single_service():
    """Test handling of exceptions during resource stats retrieval for a single service."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock get_service_resource_usage to raise an exception
    mock_get_service_resource_usage = MagicMock(side_effect=Exception("Test exception"))
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_service_resource_usage", mock_get_service_resource_usage):
        
        response = await get_resource_stats(service=ServiceName.API, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ErrorResponseModel)
        assert response.status == "error"
        assert "failed to retrieve resource stats" in response.message.lower()