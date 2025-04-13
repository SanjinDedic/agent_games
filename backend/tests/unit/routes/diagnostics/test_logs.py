import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from sqlmodel import Session

from backend.routes.diagnostics.diagnostics_router import get_logs
from backend.routes.diagnostics.diagnostics_models import ServiceName
from backend.models_api import ErrorResponseModel, ResponseModel


@pytest.mark.asyncio
async def test_get_logs_success():
    """Test successful retrieval of logs."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock log data
    mock_logs = {"line1": "INFO: Starting service", "line2": "DEBUG: Processing request"}
    mock_get_service_logs = MagicMock(return_value=mock_logs)
    mock_get_all_service_logs = MagicMock(return_value={"service1": mock_logs, "service2": mock_logs})
    
    # Test getting logs for all services
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_all_service_logs", mock_get_all_service_logs):
        
        # Pass current_user as a keyword argument
        response = await get_logs(service=ServiceName.ALL, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ResponseModel)
        assert response.status == "success"
        assert "logs" in response.data
        assert mock_get_all_service_logs.called
    
    # Test getting logs for a specific service
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_service_logs", mock_get_service_logs):
        
        # Pass current_user as a keyword argument
        response = await get_logs(service=ServiceName.API, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ResponseModel)
        assert response.status == "success"
        assert "logs" in response.data
        assert mock_get_service_logs.called


@pytest.mark.asyncio
async def test_get_logs_no_access():
    """Test logs retrieval with no Docker access."""
    # Mock dependencies
    mock_user = {"role": "institution", "institution_id": 1}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return False
    mock_check_docker_access = AsyncMock(return_value=False)
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access):
        # Pass current_user as a keyword argument
        response = await get_logs(service=ServiceName.ALL, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ErrorResponseModel)
        assert response.status == "error"
        assert "access" in response.message.lower()


@pytest.mark.asyncio
async def test_get_logs_exception():
    """Test handling of exceptions during logs retrieval."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)
    
    # Mock the check_docker_access function to return True
    mock_check_docker_access = AsyncMock(return_value=True)
    
    # Mock get_all_service_logs to raise an exception
    mock_get_all_service_logs = MagicMock(side_effect=Exception("Test exception"))
    
    with patch("backend.routes.diagnostics.diagnostics_router.check_docker_access", mock_check_docker_access), \
         patch("backend.routes.diagnostics.diagnostics_router.get_all_service_logs", mock_get_all_service_logs):
        
        # Pass current_user as a keyword argument
        response = await get_logs(service=ServiceName.ALL, current_user=mock_user, session=mock_session)
        
        assert isinstance(response, ErrorResponseModel)
        assert response.status == "error"
        assert "failed to retrieve logs" in response.message.lower()