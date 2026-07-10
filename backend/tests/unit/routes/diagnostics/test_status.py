import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from sqlmodel import Session

from backend.routes.diagnostics.diagnostics_router import get_status


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
            "valkey": {
                "name": "valkey",
                "status": "running",
                "health": "Broker connection OK",
                "is_healthy": True,
            },
            "validation-worker": {
                "name": "validation-worker",
                "status": "running",
                "health": "Worker validation@host responded to ping",
                "is_healthy": True,
            },
            "simulation-worker": {
                "name": "simulation-worker",
                "status": "running",
                "health": "Worker simulation@host responded to ping",
                "is_healthy": True,
            },
        }

        with patch(
            "backend.routes.diagnostics.diagnostics_router.get_all_services_status",
            return_value=mock_statuses,
        ) as mock_get_all_services_status:

            response = await get_status(current_user=mock_user, session=mock_session)

            assert response == {"statuses": mock_statuses}
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

        with pytest.raises(HTTPException) as exc_info:
            await get_status(current_user=mock_user, session=mock_session)

        assert exc_info.value.status_code == 403
        assert "access" in exc_info.value.detail.lower()


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

            with pytest.raises(Exception, match="Test exception"):
                await get_status(current_user=mock_user, session=mock_session)
