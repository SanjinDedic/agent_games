import pytest
import random
from unittest.mock import patch, MagicMock

from backend.database.db_models import League
from backend.games.greedy_pig.greedy_pig import GreedyPigGame
from backend.games.greedy_pig.player import Player

class TestPlayer(Player):
    """Test implementation of Player class for testing"""
    def make_decision(self, game_state):
        return "bank"  # Always bank for predictable tests


class TestRiskyPlayer(Player):
    """Test implementation that always continues"""
    def make_decision(self, game_state):
        return "continue"  # Always continue for testing risky behavior


@pytest.fixture
def test_league():
    """Create a test league for the game"""
    return League(
        name="test_league",
        game="greedy_pig"
    )


@pytest.fixture
def test_game(test_league):
    """Create a test game instance with test players"""
    game = GreedyPigGame(test_league, verbose=True)
    # Clear default players and add our test players
    game.players = []
    game.players.append(TestPlayer())
    game.players.append(TestRiskyPlayer())
    game.scores = {str(player.name): 0 for player in game.players}
    game.active_players = list(game.players)
    return game


def test_game_initialization(test_league):
    """Test that the game initializes properly"""
    game = GreedyPigGame(test_league)
    
    # Check initial state
    assert game.round_no == 0
    assert game.roll_no == 0
    assert game.game_over is False
    assert isinstance(game.active_players, list)
    assert isinstance(game.players_banked_this_round, list)
    assert isinstance(game.game_feedback, dict)
    assert game.game_feedback["game"] == "greedy_pig"
    assert isinstance(game.player_feedback, dict)
    assert isinstance(game.custom_rewards, list)


def test_roll_dice(test_game):
    """Test the dice rolling functionality"""
    # Test that dice returns a value between 1 and 6
    for _ in range(100):  # Roll many times to test randomness
        roll = test_game.roll_dice()
        assert 1 <= roll <= 6


def test_get_game_state(test_game):
    """Test that game state is correctly returned"""
    game_state = test_game.get_game_state()
    
    # Check structure of game state
    assert "round_no" in game_state
    assert "roll_no" in game_state
    assert "players_banked_this_round" in game_state
    assert "banked_money" in game_state
    assert "unbanked_money" in game_state
    
    # Check that player data is correctly included
    for player in test_game.players:
        assert player.name in game_state["banked_money"]
        assert player.name in game_state["unbanked_money"]


def test_default_rewards_winner_takes_all(test_game):
    """Default rewards give everything to first place"""
    assert test_game.custom_rewards == [10, 0, 0, 0, 0, 0, 0]


def test_assign_points(test_game):
    """Test point assignment based on player rankings"""
    # Mock a game state
    game_state = {
        "banked_money": {
            "TestPlayer": 80,
            "TestRiskyPlayer": 50,
        },
        "unbanked_money": {
            "TestPlayer": 0,
            "TestRiskyPlayer": 0,
        }
    }

    # Test with default (winner-takes-all) rewards
    results = test_game.assign_points(game_state)

    # First place takes everything, second place gets nothing
    assert results["points"]["TestPlayer"] == 10
    assert results["points"]["TestRiskyPlayer"] == 0

    # Test with custom placement rewards
    custom_rewards = [5, 3, 1]
    results = test_game.assign_points(game_state, custom_rewards)
    assert results["points"]["TestPlayer"] == 5
    assert results["points"]["TestRiskyPlayer"] == 3


def test_assign_points_multiple_over_100_higher_score_wins(test_game):
    """When several players finish over 100, the highest total wins"""
    game_state = {
        "banked_money": {
            "TestPlayer": 105,
            "TestRiskyPlayer": 150,
        },
        "unbanked_money": {
            "TestPlayer": 0,
            "TestRiskyPlayer": 0,
        }
    }

    results = test_game.assign_points(game_state)
    assert results["points"]["TestRiskyPlayer"] == 10
    assert results["points"]["TestPlayer"] == 0


def test_assign_points_tie_splits_the_pot(test_game):
    """Tied players share the pooled rewards for the placements they span"""
    game_state = {
        "banked_money": {
            "TestPlayer": 50,
            "TestRiskyPlayer": 50,
        },
        "unbanked_money": {
            "TestPlayer": 0,
            "TestRiskyPlayer": 0,
        }
    }

    # Winner-takes-all default: two tied winners split 10 + 0 → 5 each
    results = test_game.assign_points(game_state)
    assert results["points"]["TestPlayer"] == 5
    assert results["points"]["TestRiskyPlayer"] == 5

    # Placement rewards: two tied winners split 10 + 8 → 9 each
    results = test_game.assign_points(game_state, [10, 8, 6])
    assert results["points"]["TestPlayer"] == 9
    assert results["points"]["TestRiskyPlayer"] == 9

    # A tie below an outright winner splits the lower placements
    game_state = {
        "banked_money": {
            "TestPlayer": 80,
            "TestRiskyPlayer": 50,
            "ThirdPlayer": 50,
        },
        "unbanked_money": {
            "TestPlayer": 0,
            "TestRiskyPlayer": 0,
            "ThirdPlayer": 0,
        }
    }
    results = test_game.assign_points(game_state, [10, 8, 6])
    assert results["points"]["TestPlayer"] == 10
    assert results["points"]["TestRiskyPlayer"] == 7  # (8 + 6) / 2
    assert results["points"]["ThirdPlayer"] == 7


@patch('random.randint')
def test_play_round_roll_one(mock_randint, test_game):
    """Test what happens when player rolls a 1"""
    # Make the dice roll return 1
    mock_randint.return_value = 1
    
    # Give the player some unbanked money to lose
    test_game.players[1].unbanked_money = 30
    
    # Play a round
    test_game.play_round()
    
    # Check that unbanked money was reset
    assert test_game.players[1].unbanked_money == 0


@patch('random.randint')
def test_play_round_bank_decision(mock_randint, test_game):
    """Test player banking decision during a round"""
    # Make the dice roll return 6 to avoid rolling a 1
    mock_randint.return_value = 6
    
    # Play a round
    test_game.play_round()
    
    # TestPlayer should have banked
    assert test_game.players[0].name in test_game.players_banked_this_round
    # TestPlayer's banked money should include the roll
    assert test_game.players[0].banked_money == 6


@patch('random.randint')
def test_play_game_win_condition(mock_randint, test_game):
    """Test game ends once a player has BANKED 100 points"""
    # Make the dice always roll 6 for faster testing
    mock_randint.return_value = 6

    # Set player close to winning
    test_game.players[0].banked_money = 94

    # Play the game
    results = test_game.play_game()

    # Game should be over
    assert test_game.game_over is True

    # TestPlayer banks 94 + 6 = 100 on the first roll and wins immediately
    assert results["score_aggregate"]["TestPlayer"] == 100
    assert results["points"]["TestPlayer"] == 10
    # TestRiskyPlayer was still holding its 6 unbanked — lost, scores nothing
    assert results["score_aggregate"]["TestRiskyPlayer"] == 0
    assert results["points"]["TestRiskyPlayer"] == 0


@patch('random.randint')
def test_no_automated_banking_at_100(mock_randint, test_game):
    """Unbanked money over 100 does NOT end the game — you must bank to win"""
    # TestRiskyPlayer rides to 102 unbanked, then a 1 wipes it out
    mock_randint.side_effect = [6] * 17 + [1]

    test_game.play_round()

    # Crossing 100 unbanked must not have triggered a win
    assert test_game.game_over is False
    assert test_game.players[1].banked_money == 0
    assert test_game.players[1].unbanked_money == 0


@patch('random.randint')
def test_failsafe_bank_at_150(mock_randint, test_game):
    """A player holding 150 unbanked is force-banked"""
    # 25 rolls of 6 → TestRiskyPlayer reaches exactly 150 unbanked
    mock_randint.return_value = 6

    test_game.play_round()

    risky = test_game.players[1]
    assert risky.banked_money == 150
    assert risky.unbanked_money == 0
    # 150 banked ends the game at the end of the round
    assert test_game.game_over is True


def test_reset(test_game):
    """Test game reset functionality"""
    # Change game state
    test_game.round_no = 5
    test_game.roll_no = 3
    test_game.game_over = True
    test_game.players[0].banked_money = 50
    test_game.players[1].unbanked_money = 20
    
    # Reset game
    test_game.reset()
    
    # Check that state was reset
    assert test_game.round_no == 0
    assert test_game.roll_no == 0
    assert test_game.game_over is False
    assert test_game.players[0].banked_money == 0
    assert test_game.players[1].unbanked_money == 0
    assert test_game.game_feedback == {"game": "greedy_pig", "rounds": []}
    assert test_game.player_feedback == {}


def test_run_simulations(test_game):
    """Test running multiple game simulations"""
    results = test_game.run_simulations(num_simulations=3, league=None)
    
    # Check structure of results
    assert "total_points" in results
    assert "num_simulations" in results
    assert "table" in results
    
    # Check that all players have scores
    for player in test_game.players:
        assert player.name in results["total_points"]
    
    # Check simulation count is correct
    assert results["num_simulations"] == 3


def test_run_single_game_with_feedback(test_game):
    """Test running a single game with feedback enabled"""
    result = test_game.run_single_game_with_feedback()
    
    # Check structure of results
    assert "results" in result
    assert "feedback" in result
    assert "player_feedback" in result
    
    # Check that feedback was collected as dict
    assert isinstance(result["feedback"], dict)
    assert result["feedback"]["game"] == "greedy_pig"
    assert len(result["feedback"]["rounds"]) > 0