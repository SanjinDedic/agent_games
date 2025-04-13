from fastapi.testclient import TestClient


def test_root_endpoint_success(client: TestClient):
    """Test successful root endpoint response"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Server is up and running"


def test_root_endpoint_response_structure(client: TestClient):
    """Test the response structure from root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()

    # Verify response model structure
    assert isinstance(data, dict)
    assert "status" in data
    assert "message" in data
    assert isinstance(data["status"], str)
    assert isinstance(data["message"], str)


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


def test_root_endpoint_headers(client: TestClient):
    """Test response headers from root endpoint"""
    response = client.get("/")
    assert response.status_code == 200

    # Verify Content-Type header
    assert response.headers["content-type"] == "application/json"

    # Verify CORS headers if they're set in your application
    if "access-control-allow-origin" in response.headers:
        assert response.headers["access-control-allow-origin"] == "*"


def test_root_endpoint_performance(client: TestClient):
    """Test root endpoint response time"""
    # Make multiple requests to check consistency
    for _ in range(10):
        response = client.get("/")
        assert response.status_code == 200
        # Basic performance check - endpoint should respond quickly
        assert response.elapsed.total_seconds() < 0.5  # 500ms threshold


def test_root_endpoint_concurrency(client: TestClient):
    """Test root endpoint under concurrent requests"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def make_request():
        response = client.get("/")
        return response.status_code, response.json()

    # Make 50 concurrent requests
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(50)]

        for future in as_completed(futures):
            status_code, data = future.result()
            assert status_code == 200
            assert data["status"] == "success"
            assert data["message"] == "Server is up and running"
