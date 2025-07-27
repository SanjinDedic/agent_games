import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlmodel import Session

from backend.routes.diagnostics.diagnostics_router import get_status
from backend.models_api import ErrorResponseModel, ResponseModel


@pytest.mark.asyncio
async def test_status_success():
    """Test successful retrieval of status for all services."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)

    # Mock the check_docker_access function to return True
    with patch(
        "backend.routes.diagnostics.diagnostics_router.check_docker_access"
    ) as mock_check_docker_access:
        mock_check_docker_access.return_value = True

        # Mock service status data
        mock_statuses = {
            "validator": {
                "name": "validator",
                "status": "running",
                "health": "Service validator is healthy (HTTP 200)",
                "is_healthy": True,
            },
            "simulator": {
                "name": "simulator",
                "status": "running",
                "health": "Service simulator is healthy (HTTP 200)",
                "is_healthy": True,
            },
        }

        with patch(
            "backend.routes.diagnostics.diagnostics_router.get_all_services_status",
            return_value=mock_statuses,
        ) as mock_get_all_services_status:

            response = await get_status(current_user=mock_user, session=mock_session)

            assert isinstance(response, ResponseModel)
            assert response.status == "success"
            assert "statuses" in response.data
            assert mock_get_all_services_status.called


@pytest.mark.asyncio
async def test_status_no_access():
    """Test status retrieval with no Docker access."""
    # Mock dependencies
    mock_user = {"role": "institution", "institution_id": 1}
    mock_session = MagicMock(spec=Session)

    # Mock the check_docker_access function to return False
    with patch(
        "backend.routes.diagnostics.diagnostics_router.check_docker_access"
    ) as mock_check_docker_access:
        mock_check_docker_access.return_value = False

        response = await get_status(current_user=mock_user, session=mock_session)

        assert isinstance(response, ErrorResponseModel)
        assert response.status == "error"
        assert "access" in response.message.lower()


@pytest.mark.asyncio
async def test_status_exception():
    """Test handling of exceptions during status retrieval."""
    # Mock dependencies
    mock_user = {"role": "admin", "sub": "admin"}
    mock_session = MagicMock(spec=Session)

    # Mock the check_docker_access function to return True
    with patch(
        "backend.routes.diagnostics.diagnostics_router.check_docker_access"
    ) as mock_check_docker_access:
        mock_check_docker_access.return_value = True

        # Mock get_all_services_status to raise an exception
        with patch(
            "backend.routes.diagnostics.diagnostics_router.get_all_services_status",
            side_effect=Exception("Test exception"),
        ):

            response = await get_status(current_user=mock_user, session=mock_session)

            assert isinstance(response, ErrorResponseModel)
            assert response.status == "error"
            assert "failed to retrieve service status" in response.message.lower()
