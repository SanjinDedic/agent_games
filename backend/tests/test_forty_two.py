import os
import sys
import pytest
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from games.forty_two.forty_two import FortyTwoGame
from models_db import League

@pytest.fixture
def test_league():
    return League(
        name="comp_test",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        folder="leagues/admin/comp_test",
        game="forty_two"
    )

def test_game_initialization(test_league):
    game = FortyTwoGame(test_league)
    assert len(game.players) > 0
    assert all(player.name in game.scores for player in game.players)

def test_play_round(test_league):
    game = FortyTwoGame(test_league)
    player = game.players[0]
    hand = game.play_round(player)
    assert 0 <= hand <= 42

def test_play_game(test_league):
    game = FortyTwoGame(test_league)
    results = game.play_game()
    assert "points" in results
    assert all(0 <= score <= 42 for score in results["points"].values())

def test_get_game_state(test_league):
    game = FortyTwoGame(test_league)
    player = game.players[0]
    game_state = game.get_game_state(player.name, 20)
    assert "player_name" in game_state
    assert "current_hand" in game_state
    assert "scores" in game_state

def test_get_all_player_classes_from_folder(test_league):
    game = FortyTwoGame(test_league, verbose=True)
    assert len(game.players) > 0
    player_names = [player.name for player in game.players]
    print(f"Player names: {player_names}")
    # Add assertions for specific player names if you know them

def test_game_reset(test_league):
    game = FortyTwoGame(test_league)
    initial_scores = game.scores.copy()
    game.play_game()
    game.reset()
    assert game.scores == initial_scores

def test_run_simulations(test_league):
    num_simulations = 10
    results = FortyTwoGame.run_simulations(num_simulations, test_league)
    assert isinstance(results, dict)
    assert "total_points" in results
    assert "total_wins" in results["table"]
    assert "num_simulations" in results
    assert results["num_simulations"] == num_simulations

    total_wins = sum(results["table"]["total_wins"].values())
    assert total_wins == num_simulations

    for player, points in results["total_points"].items():
        assert points >= 0
        assert results["table"]["total_wins"][player] >= 0