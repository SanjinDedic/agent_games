import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.api import app

# Create test client
client = TestClient(app)

@pytest.mark.asyncio
async def test_status_success(client, auth_headers):
    """Test successful retrieval of service status."""

    # Test getting status for all services
    response = client.get("/diagnostics/status", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "statuses" in data

    # Verify the response structure
    statuses = data["statuses"]
    assert isinstance(statuses, dict)

    # Should have the broker and both worker services
    expected_services = ["valkey", "validation-worker", "simulation-worker"]
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
async def test_status_exception(client, auth_headers):
    """A failure collecting service status is no longer masked as a 200 error;
    it propagates (a 500 in production) so monitoring sees it."""

    # Mock service status functions to raise an exception
    # Need to patch it where it's imported, not where it's defined
    with patch("backend.routes.diagnostics.diagnostics_router.get_all_services_status",
               side_effect=Exception("Test exception")):

        with pytest.raises(Exception, match="Test exception"):
            client.get("/diagnostics/status", headers=auth_headers)


@pytest.mark.asyncio
async def test_status_institution_allowed(client):
    """Any institution can read service status; the per-institution docker
    access gate no longer exists."""
    from backend.routes.auth.auth_core import create_access_token
    from datetime import timedelta

    institution_token = create_access_token(
        data={"sub": "test_institution", "role": "institution", "institution_id": 999},
        expires_delta=timedelta(minutes=30),
    )

    headers = {"Authorization": f"Bearer {institution_token}"}

    response = client.get("/diagnostics/status", headers=headers)

    assert response.status_code == 200
    assert "statuses" in response.json()
