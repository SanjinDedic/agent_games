import pytest
from unittest.mock import patch

from fastapi import HTTPException

from backend.routes.auth.auth_core import require_owner
from backend.routes.diagnostics.diagnostics_router import get_status


@pytest.mark.asyncio
async def test_status_success():
    """Test successful retrieval of status for all services."""
    mock_user = {"role": "owner", "sub": "admin"}

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


def test_require_owner_rejects_other_roles():
    """The guard is a dependency now, so it is tested directly rather than by
    calling the endpoint — a bare call to get_status no longer runs it."""
    with pytest.raises(HTTPException) as exc_info:
        require_owner({"role": "student", "team_name": "some_team"})

    assert exc_info.value.status_code == 403
