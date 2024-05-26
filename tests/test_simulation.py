import os
import sys
import pytest
from unittest.mock import patch
from io import StringIO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from games.greedy_pig.greedy_pig_sim import run_simulations
from games.greedy_pig.greedy_pig import Game
from models import League

@pytest.fixture
def test_league():
    return League(folder="leagues/test_league", name="Test League")

def test_game_initialization(test_league):
    game = Game(test_league)
    assert len(game.players) == 9
    assert game.round_no == 0
    assert game.roll_no == 0
    assert not game.game_over

def test_roll_dice():
    game = Game(League(folder="leagues/test_league", name="Test League"))
    roll = game.roll_dice()
    assert 1 <= roll <= 6

def test_play_round(test_league):
    game = Game(test_league)
    initial_round = game.round_no
    print("Initial:", initial_round)
    game.play_round()
    print("After 1st round:", game.round_no)
    assert game.round_no == initial_round + 1
    for player in game.players:
        assert player.has_banked_this_turn == False

def test_play_game(test_league):
    game = Game(test_league)
    results = game.play_game()
    assert isinstance(results, dict)
    assert "points" in results
    assert "score_aggregate" in results
    assert len(results["points"]) == len(game.players)
    assert len(results["score_aggregate"]) == len(game.players)

def test_assign_points(test_league):
    game = Game(test_league)
    game_state = {
        "banked_money": {"Player1": 50, "Player2": 80, "Player3": 30, "Player4": 70},
        "unbanked_money": {"Player1": 10, "Player2": 20, "Player3": 5, "Player4": 15}
    }
    results = game.assign_points(game_state)
    assert results["points"]["Player2"] == 4
    assert results["points"]["Player4"] == 3
    assert results["points"]["Player1"] == 2
    assert results["points"]["Player3"] == 1

def test_get_all_player_classes_from_folder(test_league):
    game = Game(test_league)
    player_classes = game.get_all_player_classes_from_folder(test_league.folder)
    assert len(player_classes) == 9
    player_names = [player.name for player in player_classes]
    assert "AlwaysBank" in player_names
    assert "Bank5" in player_names
    assert "Bank10" in player_names
    assert "Bank15" in player_names
    assert "BankRoll3" in player_names
    assert "BankRoll4" in player_names
    assert "Low78" in player_names
    assert "Mid78" in player_names
    assert "Winner78" in player_names


def test_game_reset(test_league):
    game = Game(test_league)
    game.play_round()
    game.reset()
    assert game.round_no == 0
    assert game.roll_no == 0
    assert not game.game_over
    for player in game.players:
        assert player.banked_money == 0
        assert player.unbanked_money == 0
        assert not player.has_banked_this_turn

@patch('sys.stdout', new_callable=StringIO)
def test_run_simulations(mock_stdout):
    #create a test league
    test_league = League(folder="leagues/test_league", name="Test League")
    num_simulations = 10
    results = run_simulations(num_simulations,test_league)
    assert len(results["total_points"]) == 9
    for points in results["total_points"].values():
        assert isinstance(points, int)
        assert points >= 0