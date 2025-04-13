import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.api import app
from backend.routes.diagnostics.diagnostics_models import ServiceName

# Create test client
client = TestClient(app)

@pytest.mark.asyncio
async def test_resource_stats_success(client, auth_headers, ensure_containers):
    """Test successful retrieval of resource stats."""
    
    # Test getting resource stats for all services
    response = client.get("/diagnostics/resource-stats", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "resources" in data["data"]
    
    # Test getting resource stats for a specific service
    # Use the string value "api" instead of the enum reference
    response = client.get("/diagnostics/resource-stats?service=api", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "resources" in data["data"]

@pytest.mark.asyncio
async def test_resource_stats_unauthorized(client):
    """Test resource stats retrieval with no authentication."""
    
    # Try accessing the endpoint without authentication
    response = client.get("/diagnostics/resource-stats")
    
    assert response.status_code == 401
    assert "detail" in response.json()
    assert "not authenticated" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_resource_stats_exception(client, auth_headers, ensure_containers):
    """Test handling of exceptions during resource stats retrieval."""
    
    # Mock get_all_services_resource_usage to raise an exception
    with patch("backend.routes.diagnostics.diagnostics_router.get_all_services_resource_usage", 
               side_effect=Exception("Test exception")):
        
        response = client.get("/diagnostics/resource-stats", headers=auth_headers)
        
        assert response.status_code == 200  # FastAPI still returns 200 for ErrorResponseModel
        data = response.json()
        assert data["status"] == "error"
        assert "failed to retrieve resource stats" in data["message"].lower() or "error" in data["message"].lower()