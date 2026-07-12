from fastapi.testclient import TestClient


def test_root_endpoint_success(client: TestClient):
    """Test successful root endpoint response"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Server is up and running"


def test_root_endpoint_method_not_allowed(client: TestClient):
    """Test root endpoint with unsupported HTTP methods"""

    # Test POST request
    response = client.post("/")
    assert response.status_code == 405  # Method Not Allowed

    # Test PUT request
    response = client.put("/")
    assert response.status_code == 405

    # Test DELETE request
    response = client.delete("/")
    assert response.status_code == 405

    # Test PATCH request
    response = client.patch("/")
    assert response.status_code == 405
