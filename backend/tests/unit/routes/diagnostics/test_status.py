import pytest
from unittest.mock import patch

from fastapi import HTTPException

from backend.routes.diagnostics.diagnostics_router import get_status


@pytest.mark.asyncio
async def test_status_success():
    """Test successful retrieval of status for all services."""
    mock_user = {"role": "admin", "sub": "admin"}

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

        response = await get_status(current_user=mock_user)

        assert response == {"statuses": mock_statuses}
        assert mock_get_all_services_status.called


@pytest.mark.asyncio
async def test_status_institution_allowed():
    """Institutions can read service status; no per-institution gate remains."""
    mock_user = {"role": "institution", "institution_id": 1}
    mock_statuses = {"valkey": {"is_healthy": True}}

    with patch(
        "backend.routes.diagnostics.diagnostics_router.get_all_services_status",
        return_value=mock_statuses,
    ):
        response = await get_status(current_user=mock_user)

    assert response == {"statuses": mock_statuses}


@pytest.mark.asyncio
async def test_status_disallowed_role():
    """Roles outside admin/institution are rejected by the role decorator."""
    mock_user = {"role": "student", "team_name": "some_team"}

    with pytest.raises(HTTPException) as exc_info:
        await get_status(current_user=mock_user)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_status_exception():
    """Test handling of exceptions during status retrieval."""
    mock_user = {"role": "admin", "sub": "admin"}

    with patch(
        "backend.routes.diagnostics.diagnostics_router.get_all_services_status",
        side_effect=Exception("Test exception"),
    ):
        with pytest.raises(Exception, match="Test exception"):
            await get_status(current_user=mock_user)
