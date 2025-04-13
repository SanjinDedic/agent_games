import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from backend.api import app
from backend.models_api import ResponseModel, ErrorResponseModel

# Create test client
client = TestClient(app)

@pytest.mark.asyncio
async def test_basic_overview_success(client, auth_headers, ensure_containers):
    """Test successful retrieval of basic system overview."""
    
    # Test getting basic overview with proper authentication
    response = client.get("/diagnostics/basic-overview", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "system" in data["data"]
    assert "statuses" in data["data"]

@pytest.mark.asyncio
async def test_basic_overview_unauthorized(client):
    """Test basic overview retrieval with no authentication."""
    
    # Try accessing the endpoint without authentication
    response = client.get("/diagnostics/basic-overview")
    
    assert response.status_code == 401
    assert "detail" in response.json()
    assert "not authenticated" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_basic_overview_exception(client, auth_headers, ensure_containers):
    """Test handling of exceptions during basic overview retrieval."""
    
    # Mock the system resources function to raise an exception
    with patch("backend.routes.diagnostics.diagnostics_router.get_system_resources", 
               side_effect=Exception("Test exception")):
        
        response = client.get("/diagnostics/basic-overview", headers=auth_headers)
        
        assert response.status_code == 200  # FastAPI still returns 200 for ErrorResponseModel
        data = response.json()
        assert data["status"] == "error"
        assert "failed to retrieve basic overview" in data["message"].lower() or "error" in data["message"].lower()