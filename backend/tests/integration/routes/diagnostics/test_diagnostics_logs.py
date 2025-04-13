import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from backend.api import app
from backend.routes.diagnostics.diagnostics_models import ServiceName

# Create test client
client = TestClient(app)

@pytest.mark.asyncio
async def test_get_logs_success(client, auth_headers, ensure_containers):
    """Test successful retrieval of logs for a service."""
    
    # Test getting logs for all services
    response = client.get("/diagnostics/logs", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "logs" in data["data"]
    
    # Test getting logs for a specific service
    # Note: Use the string value "api" instead of the enum reference
    response = client.get("/diagnostics/logs?service=api", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "logs" in data["data"]

@pytest.mark.asyncio
async def test_get_logs_unauthorized(client):
    """Test logs retrieval with no authentication."""
    
    # Try accessing the endpoint without authentication
    response = client.get("/diagnostics/logs")
    
    assert response.status_code == 401
    assert "detail" in response.json()
    assert "not authenticated" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_get_logs_exception(client, auth_headers, ensure_containers):
    """Test handling of exceptions during logs retrieval."""
    
    # Mock the get_all_service_logs function to raise an exception
    with patch("backend.routes.diagnostics.diagnostics_router.get_all_service_logs", 
               side_effect=Exception("Test exception")):
        
        response = client.get("/diagnostics/logs", headers=auth_headers)
        
        assert response.status_code == 200  # FastAPI still returns 200 for ErrorResponseModel
        data = response.json()
        assert data["status"] == "error"
        assert "failed to retrieve logs" in data["message"].lower() or "error" in data["message"].lower()