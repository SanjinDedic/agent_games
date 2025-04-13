import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.api import app
from backend.routes.diagnostics.diagnostics_models import ServiceName

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
    
    # Test getting status for a specific service
    # Use the string value "api" instead of the enum reference
    response = client.get("/diagnostics/status?service=api", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "status" in data["data"]

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
    with patch("backend.routes.diagnostics.diagnostics_router.get_all_services_status", 
               side_effect=Exception("Test exception")):
        
        response = client.get("/diagnostics/status", headers=auth_headers)
        
        assert response.status_code == 200  # FastAPI still returns 200 for ErrorResponseModel
        data = response.json()
        assert data["status"] == "error"
        assert "failed to retrieve service status" in data["message"].lower() or "error" in data["message"].lower()