import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame
from models_db import League

@pytest.fixture
def test_league():
    return League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        folder="leagues/test_league",
        game="prisoners_dilemma"
    )

def test_game_initialization(test_league):
    game = PrisonersDilemmaGame(test_league)
    assert len(game.players) > 0
    assert isinstance(game.histories, dict)
    assert isinstance(game.scores, dict)
    assert game.rounds_per_pairing == 5

def test_add_feedback(test_league):
    game = PrisonersDilemmaGame(test_league, verbose=True)
    game.add_feedback("Test message")
    assert "Test message" in game.feedback

def test_color_decision(test_league):
    game = PrisonersDilemmaGame(test_league)
    assert 'color: green;' in game.color_decision('collude')
    assert 'color: red;' in game.color_decision('defect')
    assert game.color_decision('invalid') == 'invalid'

def test_play_pairing(test_league):
    game = PrisonersDilemmaGame(test_league, verbose=True)
    player1, player2 = game.players[:2]
    game.play_pairing(player1, player2)
    assert len(game.histories[player1.name][player2.name]) == game.rounds_per_pairing
    assert len(game.histories[player2.name][player1.name]) == game.rounds_per_pairing

def test_add_player_feedback(test_league):
    game = PrisonersDilemmaGame(test_league, verbose=True)
    player = game.players[0]
    player.feedback = ["Test feedback"]
    game.add_player_feedback(player)
    assert any("Test feedback" in msg for msg in game.feedback)
    assert not player.feedback

def test_update_scores(test_league):
    game = PrisonersDilemmaGame(test_league)
    player1, player2 = game.players[:2]
    initial_score1 = game.scores[player1.name]
    initial_score2 = game.scores[player2.name]
    game.update_scores(player1, 'collude', player2, 'defect')
    assert game.scores[player1.name] == initial_score1 + 0
    assert game.scores[player2.name] == initial_score2 + 5

def test_get_game_state(test_league):
    game = PrisonersDilemmaGame(test_league)
    player1, player2 = game.players[:2]
    state = game.get_game_state(player1.name, player2.name, 1)
    assert "round_number" in state
    assert "player_name" in state
    assert "opponent_name" in state
    assert "opponent_history" in state
    assert "my_history" in state
    assert "all_history" in state
    assert "scores" in state

def test_play_game(test_league):
    game = PrisonersDilemmaGame(test_league, verbose=True)
    results = game.play_game()
    assert "points" in results
    assert "score_aggregate" in results
    assert len(results["points"]) == len(game.players)
    assert len(game.feedback) > 0

def test_play_game_with_custom_rewards(test_league):
    game = PrisonersDilemmaGame(test_league)
    custom_rewards = [4, 0, 6, 2]
    results = game.play_game(custom_rewards)
    assert "points" in results
    assert "score_aggregate" in results

def test_reset(test_league):
    game = PrisonersDilemmaGame(test_league)
    game.play_game()
    initial_scores = game.scores.copy()
    game.reset()
    assert game.scores != initial_scores
    assert all(score == 0 for score in game.scores.values())
    assert not game.feedback

def test_run_single_game_with_feedback(test_league):
    result = PrisonersDilemmaGame.run_single_game_with_feedback(test_league)
    assert "results" in result
    assert "feedback" in result
    assert isinstance(result["feedback"], str)

@patch('sys.stdout', new_callable=StringIO)
def test_run_simulations(mock_stdout, test_league):
    num_simulations = 10
    results = PrisonersDilemmaGame.run_simulations(num_simulations, test_league)
    assert isinstance(results, dict)
    assert "total_points" in results
    assert "total_wins" in results
    assert "num_simulations" in results
    assert results["num_simulations"] == num_simulations

def test_run_simulations_with_custom_rewards(test_league):
    num_simulations = 10
    custom_rewards = [4, 0, 6, 2]
    results = PrisonersDilemmaGame.run_simulations(num_simulations, test_league, custom_rewards)
    assert isinstance(results, dict)
    assert "total_points" in results
    assert "total_wins" in results
    assert "num_simulations" in results
    assert results["num_simulations"] == num_simulations

def test_get_all_player_classes_from_folder(test_league):
    game = PrisonersDilemmaGame(test_league, verbose=True)
    assert len(game.players) > 0
    player_names = [player.name for player in game.players]
    print(f"Player names: {player_names}")
    assert "cooperator" in player_names
    assert "defector" in player_names

def test_starter_code():
    assert 'class CustomPlayer(Player):' in PrisonersDilemmaGame.starter_code
    assert 'def make_decision(self, game_state):' in PrisonersDilemmaGame.starter_code

def test_game_instructions():
    assert '<h1>Prisoner\'s Dilemma Game Instructions</h1>' in PrisonersDilemmaGame.game_instructions
    assert 'Game Objective' in PrisonersDilemmaGame.game_instructions
    assert 'Scoring' in PrisonersDilemmaGame.game_instructions
    assert 'Strategy Tips' in PrisonersDilemmaGame.game_instructions

if __name__ == "__main__":
    pytest.main()