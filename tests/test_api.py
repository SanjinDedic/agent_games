from fastapi.testclient import TestClient
import pytest
from api import app  # Import your FastAPI app
import inspect

class Testing_Player():
    def make_decision(self, game_state):
        if len(game_state['players_banked_this_round']) > 2:
            return 'bank'
        return 'continue'

@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_read_main(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Success, server is running"}


# Test the /submit_agent endpoint
def test_submit_agent(client):
    code = inspect.getsource(Testing_Player)
    response = client.post("/submit_agent", json={"team_name": "Sanjin", "password": "aaa", "code": code})
    assert response.status_code == 200
    print(response.json())