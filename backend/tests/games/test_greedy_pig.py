from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch

import pytest

from backend.database.db_models import League
from backend.games.greedy_pig.greedy_pig import GreedyPigGame


@pytest.fixture
def test_league():
    return League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
    )


def test_game_initialization(test_league):
    game = GreedyPigGame(test_league)
    assert len(game.players) == 5
    assert game.round_no == 0
    assert game.roll_no == 0
    assert not game.game_over


def test_play_round(test_league):
    game = GreedyPigGame(test_league)
    initial_round = game.round_no
    print("Initial:", initial_round)
    game.play_round()
    print("After 1st round:", game.round_no)
    assert game.round_no == initial_round + 1
    for player in game.players:
        assert player.has_banked_this_turn is False


def test_play_game(test_league):
    game = GreedyPigGame(test_league)
    results = game.play_game()
    assert isinstance(results, dict)
    assert "points" in results
    assert "score_aggregate" in results
    assert len(results["points"]) == len(game.players)
    assert len(results["score_aggregate"]) == len(game.players)


def test_assign_points(test_league):
    game = GreedyPigGame(test_league)
    game_state = {
        "banked_money": {"Player1": 50, "Player2": 80, "Player3": 30, "Player4": 70},
        "unbanked_money": {"Player1": 10, "Player2": 20, "Player3": 5, "Player4": 15},
    }
    results = game.assign_points(game_state)
    assert results["points"]["Player2"] == 10
    assert results["points"]["Player4"] == 8
    assert results["points"]["Player1"] == 6
    assert results["points"]["Player3"] == 4


def test_game_reset(test_league):
    game = GreedyPigGame(test_league)
    game.play_round()
    game.reset()
    assert game.round_no == 0
    assert game.roll_no == 0
    assert not game.game_over
    for player in game.players:
        assert player.banked_money == 0
        assert player.unbanked_money == 0
        assert not player.has_banked_this_turn


@patch("sys.stdout", new_callable=StringIO)
def test_run_simulations(mock_stdout, test_league):
    num_simulations = 10
    game = GreedyPigGame(test_league)
    results = game.run_simulations(num_simulations, test_league)
    assert isinstance(results, dict)
    assert "total_points" in results
    assert "num_simulations" in results
    assert results["num_simulations"] == num_simulations
