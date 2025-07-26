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
    with patch(
        "backend.routes.diagnostics.diagnostics_router.check_docker_access"
    ) as mock_check_docker_access:
        mock_check_docker_access.return_value = True

        # Mock log data
        mock_logs = "INFO: Starting service\nDEBUG: Processing request"

        with patch(
            "backend.routes.diagnostics.diagnostics_router.get_service_logs",
            return_value=mock_logs,
        ) as mock_get_service_logs:

            # Test getting logs for validator service
            response = await get_logs(
                service=ServiceName.VALIDATOR,
                tail=100,
                since=None,
                current_user=mock_user,
                session=mock_session,
            )

            assert isinstance(response, ResponseModel)
            assert response.status == "success"
            assert "logs" in response.data
            assert ServiceName.VALIDATOR.value in response.data["logs"]
            mock_get_service_logs.assert_called_with(
                service_name=ServiceName.VALIDATOR.value, tail=100
            )


@pytest.mark.asyncio
async def test_get_logs_no_access():
    """Test logs retrieval with no Docker access."""
    # Mock dependencies
    mock_user = {"role": "institution", "institution_id": 1}
    mock_session = MagicMock(spec=Session)

    # Mock the check_docker_access function to return False
    with patch(
        "backend.routes.diagnostics.diagnostics_router.check_docker_access"
    ) as mock_check_docker_access:
        mock_check_docker_access.return_value = False

        response = await get_logs(
            service=ServiceName.VALIDATOR,
            tail=100,
            since=None,
            current_user=mock_user,
            session=mock_session,
        )

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
    with patch(
        "backend.routes.diagnostics.diagnostics_router.check_docker_access"
    ) as mock_check_docker_access:
        mock_check_docker_access.return_value = True

        # Mock get_service_logs to raise an exception
        with patch(
            "backend.routes.diagnostics.diagnostics_router.get_service_logs",
            side_effect=Exception("Test exception"),
        ):

            response = await get_logs(
                service=ServiceName.VALIDATOR,
                tail=100,
                since=None,
                current_user=mock_user,
                session=mock_session,
            )

            assert isinstance(response, ErrorResponseModel)
            assert response.status == "error"
            assert "failed to retrieve logs" in response.message.lower()
