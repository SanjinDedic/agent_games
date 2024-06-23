# tests/test_forty_two.py

import pytest
from games.forty_two.forty_two import Game, run_simulations
from models_db import League

@pytest.fixture
def test_league():
    return League(name="forty_two_test", game="forty_two", folder="games/forty_two/leagues/test_league")

def test_game_initialization(test_league):
    game = Game(test_league)
    assert len(game.players) == 4  # We have 3 player strategies
    assert all(player.name in game.scores for player in game.players)

def test_play_round(test_league):
    game = Game(test_league)
    player = game.players[0]
    hand = game.play_round(player)
    assert 0 <= hand <= 42

def test_play_game(test_league):
    game = Game(test_league)
    results = game.play_game()
    assert "points" in results
    assert all(0 <= score <= 42 for score in results["points"].values())

def test_run_simulations(test_league):
    results = run_simulations(100, test_league)
    assert "total_points" in results
    assert "total_wins" in results
    assert "num_simulations" in results
    assert results["num_simulations"] == 100

    total_wins = sum(results["total_wins"].values())
    assert total_wins == 100  # Total wins should equal number of simulations

    for player, points in results["total_points"].items():
        assert points >= 0
        assert results["total_wins"][player] >= 0