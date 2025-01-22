from fastapi.testclient import TestClient

from backend.docker_utils.services.simulation_server import (
    aggregate_simulation_results,
    app,
)

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
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
            "league_id": 1,
            "game_name": "prisoners_dilemma",
            "num_simulations": 10,
            "custom_rewards": [4, 0, 6, 2],
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert "status" in result
    assert result["status"] == "success"
    assert "simulation_results" in result
    assert "feedback" in result


'''
def test_run_simulation_exception_handling():
    """Test different error scenarios in simulation handling"""

    # Test case 1: League not found
    response = client.post(
        "/simulate",
        json={
            "league_id": 99999,  # Non-existent league ID
            "game_name": "prisoners_dilemma",
            "num_simulations": 10,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert "detail" in result
    assert "League with ID" in result["detail"]

    # Test case 2: Invalid game configuration
    response = client.post(
        "/simulate",
        json={
            "league_id": 1,
            "game_name": "prisoners_dilemma",
            "num_simulations": -1,  # Invalid number of simulations
        },
    )
    assert response.status_code == 422
    result = response.json()
    assert "detail" in result

    # Test case 3: Runtime error during simulation
    with patch(
        "games.prisoners_dilemma.prisoners_dilemma.PrisonersDilemmaGame.play_game"
    ) as mock_play:
        mock_play.side_effect = Exception("Simulation failed")
        response = client.post(
            "/simulate",
            json={
                "league_id": 1,
                "game_name": "prisoners_dilemma",
                "num_simulations": 10,
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "error"
        assert "Simulation failed" in result["message"]
        assert "simulation_results" in result
        assert result["simulation_results"]["num_simulations"] == 10
        assert result["simulation_results"]["total_points"] == {}
        assert result["simulation_results"]["table"] == {}

    # Test case 4: Player loading error
    with patch("games.base_game.BaseGame.get_all_player_classes_via_api") as mock_load:
        mock_load.side_effect = Exception("Failed to load players")
        response = client.post(
            "/simulate",
            json={
                "league_id": 1,
                "game_name": "prisoners_dilemma",
                "num_simulations": 10,
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "error"
        assert "Failed to load players" in result["message"]
'''
