from fastapi.testclient import TestClient
import os,sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api import app

client = TestClient(app)

def test_team_login():
    response = client.post("/team_login", json={"name": "BrunswickSC1","school_name": "ABC", "password": "ighEMkOP"})
    assert response.status_code == 200
    assert "access_token" in response.json()

    response = client.post("/team_login", json={"name": "BrunswickSC1","school_name": "ABC", "password": "wrongpass"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "No team found with these credentials"}

    response = client.post("/team_login", json={"team": "BrunswickSC1","school_name": "ABC", "password": "wrongpass"})
    assert response.status_code == 422

    response = client.post("/team_login", json={"name": "BrunswickSC1","school_name": "ABC", "password": ""})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are empty"}