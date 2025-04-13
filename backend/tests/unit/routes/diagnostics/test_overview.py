import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlmodel import Session

from backend.routes.diagnostics.diagnostics_router import get_overview
from backend.models_api import ErrorResponseModel, ResponseModel


@pytest.mark.asyncio
async def test_overview_success():
    """Test successful retrieval of comprehensive system overview."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock resource usage data
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
    
    # Mock system status data
    mock_statuses = {
        "service1": {"status": "running", "health": "healthy"},
        "service2": {"status": "running", "health": "healthy"}
    }
    
    # Mock system resources data
    mock_system_resources = {
        "memory": {"total": "16GB", "used": "8GB", "percent": 50.0},
        "cpu": {"percent": 25.0},
        "disk": {"total": "500GB", "used": "200GB", "percent": 40.0}
    }
    
    # Create mocks for the function calls
    mock_get_all_services_resource_usage = MagicMock(return_value=mock_service_usage)
    mock_get_all_services_status = MagicMock(return_value=mock_statuses)
    mock_get_system_resources = MagicMock(return_value=mock_system_resources)
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_all_services_resource_usage", mock_get_all_services_resource_usage), \
         patch("backend.routes.diagnostics.diagnostics_router.get_all_services_status", mock_get_all_services_status), \
         patch("backend.routes.diagnostics.diagnostics_router.get_system_resources", mock_get_system_resources):
        
        response = await get_overview(current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ResponseModel)
        assert response.status == "success"
        assert "resources" in response.data
        assert "statuses" in response.data
        assert "system" in response.data
        assert mock_get_all_services_resource_usage.called
        assert mock_get_all_services_status.called
        assert mock_get_system_resources.called


@pytest.mark.asyncio
async def test_overview_no_access():
    """Test overview retrieval with no Docker access."""
    # Mock dependencies
    mock_user = {"role": "institution", "institution_id": 1}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return False
    mock_check_docker_access = AsyncMock(return_value=False)
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access):
        response = await get_overview(current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ErrorResponseModel)
        assert response.status == "error"
        assert "access" in response.message.lower()


@pytest.mark.asyncio
async def test_overview_exception():
    """Test handling of exceptions during overview retrieval."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock get_all_services_resource_usage to raise an exception
    mock_get_all_services_resource_usage = MagicMock(side_effect=Exception("Test exception"))
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_all_services_resource_usage", mock_get_all_services_resource_usage):
        
        response = await get_overview(current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ErrorResponseModel)
        assert response.status == "error"
        assert "failed to retrieve system overview" in response.message.lower()