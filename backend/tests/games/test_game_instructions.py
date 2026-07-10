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
    assert "starter_code" in data
    assert "game_instructions" in data
    assert "Greedy Pig Game Instructions" in data["game_instructions"]


def test_get_game_instructions_non_existent_game():
    response = client.post(
        "user/get-game-instructions", json={"game_name": "non_existent_game"}
    )
    assert response.status_code == 400
    assert "Unknown game" in response.json()["detail"]


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
        starter_code = response.json()["starter_code"]
        assert "CustomPlayer" in starter_code
        if game == "arena_champions":
            assert "make_combat_decision" in starter_code
        else:
            assert "make_decision" in starter_code


def test_game_instructions_content():
    for game in GAMES:
        if game in ("lineup4", "arena_champions"):
            continue
        response = client.post("user/get-game-instructions", json={"game_name": game})
        assert response.status_code == 200
        instructions = response.json()["game_instructions"]
        assert "Game Objective" in instructions
        assert "Your Task" in instructions
        assert "Available Information" in instructions
        assert "Strategy Tips" in instructions
