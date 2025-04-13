import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.api import app

# Create test client
client = TestClient(app)

@pytest.mark.asyncio
async def test_overview_success(client, auth_headers, ensure_containers):
    """Test successful retrieval of comprehensive system overview."""
    
    # Test getting overview with proper authentication
    response = client.get("/diagnostics/overview", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "resources" in data["data"]
    assert "statuses" in data["data"]
    assert "system" in data["data"]

@pytest.mark.asyncio
async def test_overview_unauthorized(client):
    """Test overview retrieval with no authentication."""
    
    # Try accessing the endpoint without authentication
    response = client.get("/diagnostics/overview")
    
    assert response.status_code == 401
    assert "detail" in response.json()
    assert "not authenticated" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_overview_exception(client, auth_headers, ensure_containers):
    """Test handling of exceptions during overview retrieval."""
    
    # Mock get_all_services_resource_usage to raise an exception
    with patch("backend.routes.diagnostics.diagnostics_router.get_all_services_resource_usage", 
               side_effect=Exception("Test exception")):
        
        response = client.get("/diagnostics/overview", headers=auth_headers)
        
        assert response.status_code == 200  # FastAPI still returns 200 for ErrorResponseModel
        data = response.json()
        assert data["status"] == "error"
        assert "failed to retrieve system overview" in data["message"].lower() or "error" in data["message"].lower()