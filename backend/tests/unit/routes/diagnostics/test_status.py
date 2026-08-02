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
            "health": "Valkey connection OK",
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
async def test_status_disallowed_role():
    """Roles outside admin/institution are rejected by the role decorator."""
    mock_user = {"role": "student", "team_name": "some_team"}

    with pytest.raises(HTTPException) as exc_info:
        await get_status(current_user=mock_user)

    assert exc_info.value.status_code == 403
