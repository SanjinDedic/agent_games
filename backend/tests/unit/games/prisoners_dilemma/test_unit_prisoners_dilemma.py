import pytest
import random
from unittest.mock import patch, MagicMock

from backend.database.db_models import League
from backend.games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame
from backend.games.prisoners_dilemma.player import Player


class TestColluder(Player):
    """Test player that always colludes"""
    def make_decision(self, game_state):
        return "collude"


class TestDefector(Player):
    """Test player that always defects"""
    def make_decision(self, game_state):
        return "defect"


class TestTitForTat(Player):
    """Test player that starts with collude then copies opponent's last move"""
    def make_decision(self, game_state):
        if not game_state["opponent_history"]:
            return "collude"
        return game_state["opponent_history"][-1]


@pytest.fixture
def test_league():
    """Create a test league for the game"""
    return League(
        name="test_league",
        game="prisoners_dilemma"
    )


@pytest.fixture
def test_game(test_league):
    """Create a test game instance with test players"""
    game = PrisonersDilemmaGame(test_league, verbose=True)
    # Clear default players and add our test players
    game.players = []
    game.players.append(TestColluder())
    game.players.append(TestDefector())
    game.players.append(TestTitForTat())
    game.initialize_histories_and_scores()
    return game


def test_game_initialization(test_league):
    """Test that the game initializes properly"""
    game = PrisonersDilemmaGame(test_league)
    
    # Check initial state
    assert isinstance(game.reward_matrix, dict)
    assert game.rounds_per_pairing == 5
    assert isinstance(game.game_feedback, dict)
    assert isinstance(game.player_feedback, dict)
    assert game.collect_player_feedback is True
    
    # Check reward matrix values
    assert game.reward_matrix["collude,collude"] == (4, 4)
    assert game.reward_matrix["collude,defect"] == (0, 6)
    assert game.reward_matrix["defect,collude"] == (6, 0)
    assert game.reward_matrix["defect,defect"] == (0, 0)


def test_initialize_histories_and_scores(test_game):
    """Test history and score initialization"""
    # Manually reset and initialize
    test_game.reset()
    test_game.initialize_histories_and_scores()
    
    # Check that each player has an entry in histories and scores
    for player in test_game.players:
        assert str(player.name) in test_game.histories
        assert str(player.name) in test_game.scores
        assert test_game.scores[str(player.name)] == 0
        assert isinstance(test_game.histories[str(player.name)], dict)


def test_get_game_state(test_game):
    """Test game state generation for a player"""
    # Set up some history data
    player1 = test_game.players[0]
    player2 = test_game.players[1]
    p1_name = str(player1.name)
    p2_name = str(player2.name)
    
    test_game.histories[p1_name][p2_name] = ["collude", "defect"]
    test_game.histories[p2_name][p1_name] = ["defect", "defect"]
    test_game.scores[p1_name] = 4
    test_game.scores[p2_name] = 12
    
    # Get the game state for player 1
    state = test_game.get_game_state(player1.name, player2.name, 3)
    
    # Check the state structure
    assert state["round_number"] == 3
    assert state["player_name"] == p1_name
    assert state["opponent_name"] == p2_name
    assert state["opponent_history"] == ["defect", "defect"]
    assert state["my_history"] == ["collude", "defect"]
    assert state["scores"][p1_name] == 4
    assert state["scores"][p2_name] == 12


def test_play_pairing(test_game):
    """Test playing rounds between two players"""
    player1 = test_game.players[0]  # TestColluder
    player2 = test_game.players[1]  # TestDefector
    
    # Play a pairing between these two players
    test_game.play_pairing(player1, player2)
    
    # Check that the history was updated
    p1_name = str(player1.name)
    p2_name = str(player2.name)
    
    assert len(test_game.histories[p1_name][p2_name]) == test_game.rounds_per_pairing
    assert len(test_game.histories[p2_name][p1_name]) == test_game.rounds_per_pairing
    
    # Check that all decisions match the player strategies
    assert all(decision == "collude" for decision in test_game.histories[p1_name][p2_name])
    assert all(decision == "defect" for decision in test_game.histories[p2_name][p1_name])
    
    # Check scores
    # Colluder should get 0 each round, Defector should get 6 each round
    expected_p1_score = 0 * test_game.rounds_per_pairing
    expected_p2_score = 6 * test_game.rounds_per_pairing
    assert test_game.scores[p1_name] == expected_p1_score
    assert test_game.scores[p2_name] == expected_p2_score


def test_play_game(test_game):
    """Test playing a complete game with all players"""
    # Play the game
    results = test_game.play_game()
    
    # Check that results contain points for all players
    assert "points" in results
    assert "score_aggregate" in results
    
    for player in test_game.players:
        assert str(player.name) in results["points"]
        assert str(player.name) in results["score_aggregate"]
    
    # Check that game feedback was recorded
    assert "game_info" in test_game.game_feedback
    assert "players" in test_game.game_feedback["game_info"]
    assert "reward_matrix" in test_game.game_feedback["game_info"]
    assert "final_scores" in test_game.game_feedback
    
    # Check that all pairings were played
    expected_pairings = len(list(test_game.players)) * (len(list(test_game.players)) - 1) // 2
    assert len(test_game.game_feedback["pairings"]) == expected_pairings


def test_custom_rewards(test_game):
    """Test game with custom reward matrix"""
    custom_rewards = [2, 0, 5, 1]  # C-C, C-D, D-C, D-D
    
    # Play the game with custom rewards
    results = test_game.play_game(custom_rewards=custom_rewards)
    
    # Check that the reward matrix was updated
    assert test_game.reward_matrix["collude,collude"] == (2, 2)
    assert test_game.reward_matrix["collude,defect"] == (0, 5)
    assert test_game.reward_matrix["defect,collude"] == (5, 0)
    assert test_game.reward_matrix["defect,defect"] == (1, 1)


def test_tit_for_tat_strategy(test_game):
    """Test the Tit-for-Tat player against Defector"""
    player1 = test_game.players[2]  # TestTitForTat
    player2 = test_game.players[1]  # TestDefector
    
    # Reset the game
    test_game.reset()
    test_game.initialize_histories_and_scores()
    
    # Play a pairing between these two players
    test_game.play_pairing(player1, player2)
    
    # Check that the history matches Tit-for-Tat behavior
    p1_name = str(player1.name)
    p2_name = str(player2.name)
    
    # First move should be collude, then should copy opponent's previous moves
    assert test_game.histories[p1_name][p2_name][0] == "collude"
    for i in range(1, test_game.rounds_per_pairing):
        assert test_game.histories[p1_name][p2_name][i] == test_game.histories[p2_name][p1_name][i-1]


def test_reset(test_game):
    """Test game reset functionality"""
    # Play a game to set up state
    test_game.play_game()
    
    # Check that state is not empty
    assert len(test_game.game_feedback["pairings"]) > 0
    assert sum(test_game.scores.values()) > 0
    
    # Reset game
    test_game.reset()
    
    # Check that state was reset
    assert test_game.game_feedback == {"pairings": []}
    assert test_game.player_feedback == {}
    assert all(score == 0 for score in test_game.scores.values())
    assert all(len(opponents) == 0 for opponents in test_game.histories.values())


def test_run_simulations(test_game):
    """Test running multiple game simulations"""
    results = test_game.run_simulations(num_simulations=3, league=None)
    
    # Check structure of results
    assert "total_points" in results
    assert "num_simulations" in results
    assert "table" in results
    assert "defections" in results["table"]
    assert "collusions" in results["table"]
    
    # Check that all players have scores
    for player in test_game.players:
        assert str(player.name) in results["total_points"]
        assert str(player.name) in results["table"]["defections"]
        assert str(player.name) in results["table"]["collusions"]
    
    # Check simulation count is correct
    assert results["num_simulations"] == 3


def test_run_single_game_with_feedback(test_game):
    """Test running a single game with feedback enabled"""
    result = test_game.run_single_game_with_feedback()
    
    # Check structure of results
    assert "results" in result
    assert "feedback" in result
    assert "player_feedback" in result
    
    # Check that feedback was collected
    assert result["feedback"] == test_game.game_feedback
    assert result["player_feedback"] == test_game.player_feedback


def test_add_player_feedback(test_game):
    """Test adding player feedback during a game"""
    player1 = test_game.players[0]
    player2 = test_game.players[1]
    
    # Add feedback to a player
    player1.add_feedback("Test feedback message")
    
    # Call the add_player_feedback method
    test_game.add_player_feedback(player1, 1, player2.name)
    
    # Check that feedback was recorded
    p1_name = str(player1.name)
    p2_name = str(player2.name)
    
    assert p1_name in test_game.player_feedback
    assert len(test_game.player_feedback[p1_name]) == 1
    assert test_game.player_feedback[p1_name][0]["round"] == 1
    assert test_game.player_feedback[p1_name][0]["opponent"] == p2_name
    assert "Test feedback message" in test_game.player_feedback[p1_name][0]["messages"]
    
    # Player's feedback list should be emptied
    assert player1.feedback == []