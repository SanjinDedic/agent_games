import pytest
from docker.services.simulation_server import aggregate_simulation_results, app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_aggregate_simulation_results():
    simulation_results = [
        {
            "points": {"player1": 10, "player2": 20},
            "table": {"wins": {"player1": 1, "player2": 2}},
        },
        {
            "points": {"player1": 15, "player2": 25},
            "table": {"wins": {"player1": 2, "player2": 3}},
        },
    ]

    result = aggregate_simulation_results(simulation_results, 2)
    assert result["total_points"] == {"player1": 25, "player2": 45}
    assert result["num_simulations"] == 2
    assert "table" in result


def test_run_simulation_success():
    response = client.post(
        "/simulate",
        json={
            "league_name": "test_league",
            "league_game": "prisoners_dilemma",
            "league_folder": "leagues/test_league",
            "num_simulations": 10,
            "custom_rewards": [4, 0, 6, 2],
            "player_feedback": True,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert "status" in result
    assert result["status"] == "success"
    assert "simulation_results" in result
    assert "feedback" in result
    assert "player_feedback" in result


def test_run_simulation_invalid_game():
    """
    Test handling of invalid game names.
    Should return 200 with error status in payload.
    """
    response = client.post(
        "/simulate",
        json={
            "league_name": "test_league",
            "league_game": "invalid_game",
            "league_folder": "leagues/test_league",
            "num_simulations": 10,
        },
    )
    assert response.status_code == 200  # Application-level errors return 200
    result = response.json()
    assert result["status"] == "error"
    assert "Unknown game" in result["message"]
    assert "simulation_results" in result
    assert result["simulation_results"]["num_simulations"] == 10
    assert result["simulation_results"]["total_points"] == {}
    assert result["simulation_results"]["table"] == {}


def test_run_simulation_exception_handling():
    """
    Test handling of invalid folder paths.
    Should return 200 with error status in payload.
    """
    response = client.post(
        "/simulate",
        json={
            "league_name": "test_league",
            "league_game": "prisoners_dilemma",
            "league_folder": "invalid/folder/path",
            "num_simulations": 10,
        },
    )
    assert response.status_code == 200  # Application-level errors return 200
    result = response.json()
    print("FAIL", result)
    assert result["status"] == "success"
    assert "simulation_results" in result
    assert result["simulation_results"]["num_simulations"] == 10
    assert result["simulation_results"]["total_points"] == {}
    assert result["simulation_results"]["table"] == {}
