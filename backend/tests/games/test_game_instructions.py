from fastapi.testclient import TestClient

from backend.api import app
from backend.config import GAMES

client = TestClient(app)


def test_get_game_instructions_greedy_pig():
    response = client.post(
        "user/get-game-instructions", json={"game_name": "greedy_pig"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "starter_code" in data["data"]
    assert "game_instructions" in data["data"]
    assert "Greedy Pig Game Instructions" in data["data"]["game_instructions"]


def test_get_game_instructions_non_existent_game():
    response = client.post(
        "user/get-game-instructions", json={"game_name": "non_existent_game"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "Unknown game" in data["message"]


def test_get_game_instructions_missing_game_name():
    response = client.post("user/get-game-instructions", json={})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("game_name" in error["loc"] for error in data["detail"])


def test_get_game_instructions_empty_game_name():
    response = client.post("user/get-game-instructions", json={"game_name": ""})
    assert response.status_code == 422
    data = response.json()
    print(data, "for empty game name")
    assert "detail" in data
    assert "Game name must not be empty" in str(data["detail"])


def test_starter_code_content():
    for game in GAMES:
        response = client.post("user/get-game-instructions", json={"game_name": game})
        assert response.status_code == 200
        data = response.json()
        starter_code = data["data"]["starter_code"]
        assert "CustomPlayer" in starter_code
        assert "make_decision" in starter_code


def test_game_instructions_content():
    for game in GAMES:
        if game == "lineup4":
            continue
        response = client.post("user/get-game-instructions", json={"game_name": game})
        assert response.status_code == 200
        data = response.json()
        instructions = data["data"]["game_instructions"]
        assert "Game Objective" in instructions
        assert "Your Task" in instructions
        assert "Available Information" in instructions
        assert "Strategy Tips" in instructions
