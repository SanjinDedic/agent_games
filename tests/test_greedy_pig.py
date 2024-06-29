import os
import sys
import pytest
from unittest.mock import patch
from io import StringIO
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from games.greedy_pig.greedy_pig import draw_table, animate_simulations, GreedyPigGame, run_simulations as run_greedy_pig_simulations
from models_db import League

@pytest.fixture
def test_league():
    return League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        folder="leagues/test_league",
        game="greedy_pig"
    )

def test_game_initialization(test_league):
    game = GreedyPigGame(test_league)
    assert len(game.players) == 9
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
        assert player.has_banked_this_turn == False

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
        "unbanked_money": {"Player1": 10, "Player2": 20, "Player3": 5, "Player4": 15}
    }
    results = game.assign_points(game_state)
    assert results["points"]["Player2"] == 10
    assert results["points"]["Player4"] == 8
    assert results["points"]["Player1"] == 6
    assert results["points"]["Player3"] == 4

def test_get_all_player_classes_from_folder(test_league):
    game = GreedyPigGame(test_league, verbose=True)
    assert len(game.players) == 9
    player_names = [player.name for player in game.players]
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

@patch('sys.stdout', new_callable=StringIO)
def test_run_simulations(mock_stdout, test_league):
    num_simulations = 10
    results = run_greedy_pig_simulations(num_simulations, test_league)
    assert isinstance(results, dict)
    assert "total_points" in results
    assert "total_wins" in results
    assert "num_simulations" in results
    assert results["num_simulations"] == num_simulations


def test_draw_table(capsys):
    rankings = [
        ("Player1", 100),
        ("Player2", 90),
        ("Player3", 80),
        ("Player4", 70),
    ]

    draw_table(rankings)
    captured = capsys.readouterr()

    # Remove extra whitespace from the captured output
    lines = [line.strip() for line in captured.out.split('\n') if line.strip()]

    assert len(lines) >= 7  # Header, separator, 4 players, footer
    assert lines[0] == "-" * 50
    assert "Player" in lines[1] and "Points" in lines[1] and "Rank" in lines[1]  # Header line
    assert lines[2] == "-" * 50  # Separator line
    assert "Player1" in lines[3]
    assert "Player2" in lines[4]
    assert "Player3" in lines[5]
    assert "Player4" in lines[6]
    assert lines[-1] == "-" * 50  # Footer line

    # Print the captured output for debugging
    print("\nCaptured output:")
    print(captured.out)


@patch('time.sleep')  # Patch time.sleep to speed up the test
def test_animate_simulations(mock_sleep, capsys, test_league):
    num_simulations = 5
    refresh_number = 2

    animate_simulations(num_simulations, refresh_number, test_league)
    captured = capsys.readouterr()

    assert "Rankings after 2 simulations:" in captured.out
    assert "Rankings after 4 simulations:" in captured.out
    assert "Rankings after 5 simulations:" in captured.out