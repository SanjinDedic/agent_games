from datetime import datetime, timedelta

import pytest
from database.db_models import League
from games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame


@pytest.fixture
def test_league():
    return League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        folder="leagues/test_league",
        game="prisoners_dilemma",
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
    assert "Test message" in game.game_feedback["pairings"]


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
    game.add_player_feedback(player, 1, game.players[1].name)
    assert any(
        "Test feedback" in str(entry["messages"])
        for entry in game.player_feedback[player.name]
    )
    assert not player.feedback


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
    assert len(game.game_feedback["pairings"]) > 0


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
    assert game.game_feedback == {"pairings": []}
    assert game.player_feedback == {}


def test_run_single_game_with_feedback(test_league):
    result = PrisonersDilemmaGame.run_single_game_with_feedback(test_league)
    assert "results" in result
    assert "feedback" in result
    assert isinstance(result["feedback"], dict)
    assert "pairings" in result["feedback"]
    assert "game_info" in result["feedback"]


def test_run_simulations(test_league):
    num_simulations = 10
    results = PrisonersDilemmaGame.run_simulations(num_simulations, test_league)
    assert isinstance(results, dict)
    assert "total_points" in results
    assert "defections" in results["table"]
    assert "collusions" in results["table"]
    assert "num_simulations" in results
    assert results["num_simulations"] == num_simulations


def test_run_simulations_with_custom_rewards(test_league):
    num_simulations = 10
    custom_rewards = [4, 0, 6, 2]
    results = PrisonersDilemmaGame.run_simulations(
        num_simulations, test_league, custom_rewards
    )
    assert isinstance(results, dict)
    assert "total_points" in results
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
    assert "class CustomPlayer(Player):" in PrisonersDilemmaGame.starter_code
    assert "def make_decision(self, game_state):" in PrisonersDilemmaGame.starter_code


def test_game_instructions():
    assert (
        "Prisoner's Dilemma Game Instructions" in PrisonersDilemmaGame.game_instructions
    )
    assert "Game Objective" in PrisonersDilemmaGame.game_instructions
    assert "Scoring" in PrisonersDilemmaGame.game_instructions
    assert "Strategy Tips" in PrisonersDilemmaGame.game_instructions


def test_invalid_player_decision(test_league):
    game = PrisonersDilemmaGame(test_league, verbose=True)
    player1, player2 = game.players[:2]

    # Mock player1's make_decision method to return an invalid decision
    def mock_decision(game_state):
        return "invalid_decision"

    player1.make_decision = mock_decision

    # Play a pairing and verify the invalid decision is handled correctly
    game.play_pairing(player1, player2)

    # Check if the decision defaulted to 'collude'
    assert game.histories[player1.name][player2.name][0] == "collude"
    assert len(game.game_feedback["pairings"]) > 0

    # Check pairing data for invalid decision handling
    assert any(
        "round_number" in pairing["rounds"][0]
        for pairing in game.game_feedback["pairings"]
    )


def test_player_decision_exception(test_league):
    game = PrisonersDilemmaGame(test_league, verbose=True)
    player1, player2 = game.players[:2]

    # Mock player1's make_decision method to raise an exception
    def mock_decision(game_state):
        raise Exception("Test exception")

    player1.make_decision = mock_decision

    # Play a pairing and verify the exception is handled correctly
    game.play_pairing(player1, player2)

    # Check if the decision defaulted to 'collude'
    assert game.histories[player1.name][player2.name][0] == "collude"
    assert len(game.game_feedback["pairings"]) > 0

    # Check pairing data for exception handling
    assert any(
        "round_number" in pairing["rounds"][0]
        for pairing in game.game_feedback["pairings"]
    )
