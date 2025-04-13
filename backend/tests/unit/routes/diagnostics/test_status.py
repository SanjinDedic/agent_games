import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlmodel import Session

from backend.routes.diagnostics.diagnostics_router import get_status
from backend.routes.diagnostics.diagnostics_models import ServiceName
from backend.models_api import ErrorResponseModel, ResponseModel


@pytest.mark.asyncio
async def test_status_success_all_services():
    """Test successful retrieval of status for all services."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock service status data for all services
    mock_statuses = {
        "service1": {
            "container_id": "container123",
            "name": "service1",
            "status": "running",
            "health": "healthy",
            "ports": ["8000:8000"],
            "created": "2025-04-10T10:00:00Z",
            "image": "service1:latest"
        },
        "service2": {
            "container_id": "container456",
            "name": "service2",
            "status": "running",
            "health": "healthy",
            "ports": ["8001:8001"],
            "created": "2025-04-10T10:00:00Z",
            "image": "service2:latest"
        }
    }
    
    # Create mock for get_all_services_status
    mock_get_all_services_status = MagicMock(return_value=mock_statuses)
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_all_services_status", mock_get_all_services_status):
        
        # Pass parameters as keyword arguments
        response = await get_status(service=None, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ResponseModel)
        assert response.status == "success"
        assert "statuses" in response.data
        assert mock_get_all_services_status.called


@pytest.mark.asyncio
async def test_status_success_single_service():
    """Test successful retrieval of status for a single service."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock service status data for a single service
    mock_status = {
        "container_id": "container123",
        "name": "api",
        "status": "running",
        "health": "healthy",
        "ports": ["8000:8000"],
        "created": "2025-04-10T10:00:00Z",
        "image": "api:latest"
    }
    
    # Create mock for get_service_status
    mock_get_service_status = MagicMock(return_value=mock_status)
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_service_status", mock_get_service_status):
        
        # Pass parameters as keyword arguments
        response = await get_status(service=ServiceName.API, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ResponseModel)
        assert response.status == "success"
        assert "status" in response.data
        assert mock_get_service_status.called
        mock_get_service_status.assert_called_with(ServiceName.API.value)


@pytest.mark.asyncio
async def test_status_no_access():
    """Test status retrieval with no Docker access."""
    # Mock dependencies
    mock_user = {"role": "institution", "institution_id": 1}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return False
    mock_check_docker_access = AsyncMock(return_value=False)
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access):
        # Pass parameters as keyword arguments
        response = await get_status(service=None, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ErrorResponseModel)
        assert response.status == "error"
        assert "access" in response.message.lower()


@pytest.mark.asyncio
async def test_status_exception_all_services():
    """Test handling of exceptions during status retrieval for all services."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock get_all_services_status to raise an exception
    mock_get_all_services_status = MagicMock(side_effect=Exception("Test exception"))
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_all_services_status", mock_get_all_services_status):
        
        # Pass parameters as keyword arguments
        response = await get_status(service=None, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ErrorResponseModel)
        assert response.status == "error"
        assert "failed to retrieve service status" in response.message.lower()


@pytest.mark.asyncio
async def test_status_exception_single_service():
    """Test handling of exceptions during status retrieval for a single service."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock get_service_status to raise an exception
    mock_get_service_status = MagicMock(side_effect=Exception("Test exception"))
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_service_status", mock_get_service_status):
        
        # Pass parameters as keyword arguments
        response = await get_status(service=ServiceName.API, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ErrorResponseModel)
        assert response.status == "error"
        assert "failed to retrieve service status" in response.message.lower()