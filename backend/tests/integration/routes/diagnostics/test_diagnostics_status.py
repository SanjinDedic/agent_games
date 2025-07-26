import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.api import app

# Create test client
client = TestClient(app)

@pytest.mark.asyncio
async def test_status_success(client, auth_headers, ensure_containers):
    """Test successful retrieval of service status."""

    # Test getting status for all services
    response = client.get("/diagnostics/status", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "statuses" in data["data"]

    # Verify the response structure
    statuses = data["data"]["statuses"]
    assert isinstance(statuses, dict)

    # Should have validator and simulator services
    expected_services = ["validator", "simulator"]
    for service in expected_services:
        if service in statuses:
            assert "name" in statuses[service]
            assert "status" in statuses[service]
            assert "health" in statuses[service]
            assert "is_healthy" in statuses[service]

@pytest.mark.asyncio
async def test_status_unauthorized(client):
    """Test status retrieval with no authentication."""
    
    # Try accessing the endpoint without authentication
    response = client.get("/diagnostics/status")
    
    assert response.status_code == 401
    assert "detail" in response.json()
    assert "not authenticated" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_status_exception(client, auth_headers, ensure_containers):
    """Test handling of exceptions during status retrieval."""

    # Mock service status functions to raise an exception
    # Need to patch it where it's imported, not where it's defined
    with patch("backend.routes.diagnostics.diagnostics_router.get_all_services_status", 
               side_effect=Exception("Test exception")):

        response = client.get("/diagnostics/status", headers=auth_headers)

        assert response.status_code == 200  # FastAPI still returns 200 for ErrorResponseModel
        data = response.json()
        assert data["status"] == "error"
        assert "failed to retrieve service status" in data["message"].lower() or "error" in data["message"].lower()


@pytest.mark.asyncio
async def test_status_no_docker_access(client):
    """Test status retrieval without docker access."""
    # Create a token for institution without docker access
    from backend.routes.auth.auth_core import create_access_token
    from datetime import timedelta

    # Mock an institution user without docker access
    institution_token = create_access_token(
        data={"sub": "test_institution", "role": "institution", "institution_id": 999},
        expires_delta=timedelta(minutes=30),
    )

    headers = {"Authorization": f"Bearer {institution_token}"}

    # Mock the institution to not have docker access
    with patch(
        "backend.routes.diagnostics.diagnostics_router.check_docker_access"
    ) as mock_check:
        mock_check.return_value = False

        response = client.get("/diagnostics/status", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "access" in data["message"].lower()
