import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlmodel import Session

from backend.routes.diagnostics.diagnostics_router import get_basic_overview
from backend.models_api import ErrorResponseModel, ResponseModel


@pytest.mark.asyncio
async def test_basic_overview_success():
    """Test successful retrieval of basic system overview."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock system resources and services status data
    mock_system_resources = {
        "memory": {"total": "16GB", "used": "8GB", "percent": 50.0},
        "cpu": {"percent": 25.0},
        "disk": {"total": "500GB", "used": "200GB", "percent": 40.0}
    }
    
    mock_services_status = {
        "service1": {"status": "running", "health": "healthy"},
        "service2": {"status": "running", "health": "healthy"}
    }
    
    # Create mocks for the function calls
    mock_get_system_resources = MagicMock(return_value=mock_system_resources)
    mock_get_all_services_status = MagicMock(return_value=mock_services_status)
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_system_resources", mock_get_system_resources), \
         patch("backend.routes.diagnostics.diagnostics_router.get_all_services_status", mock_get_all_services_status):
        
        # Pass current_user as a keyword argument
        response = await get_basic_overview(current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ResponseModel)
        assert response.status == "success"
        assert "system" in response.data
        assert "statuses" in response.data
        assert mock_get_system_resources.called
        assert mock_get_all_services_status.called


@pytest.mark.asyncio
async def test_basic_overview_no_access():
    """Test basic overview retrieval with no Docker access."""
    # Mock dependencies
    mock_user = {"role": "institution", "institution_id": 1}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return False
    mock_check_docker_access = AsyncMock(return_value=False)
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access):
        # Pass current_user as a keyword argument
        response = await get_basic_overview(current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ErrorResponseModel)
        assert response.status == "error"
        assert "access" in response.message.lower()


@pytest.mark.asyncio
async def test_basic_overview_exception():
    """Test handling of exceptions during basic overview retrieval."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock get_system_resources to raise an exception
    mock_get_system_resources = MagicMock(side_effect=Exception("Test exception"))
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_system_resources", mock_get_system_resources):
        
        # Pass current_user as a keyword argument
        response = await get_basic_overview(current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ErrorResponseModel)
        assert response.status == "error"
        assert "failed to retrieve basic overview" in response.message.lower()