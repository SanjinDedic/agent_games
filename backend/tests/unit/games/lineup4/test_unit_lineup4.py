import pytest
import string
from unittest.mock import patch, MagicMock

from backend.database.db_models import League
from backend.games.lineup4.lineup4 import Lineup4Game
from backend.games.lineup4.player import Player


class TestRandomPlayer(Player):
    """Test player that makes random valid moves"""
    def make_decision(self, game_state):
        # Always choose the first available move for predictable tests
        return game_state["possible_moves"][0]


class TestColumnPlayer(Player):
    """Test player that always tries to play in column 1"""
    def make_decision(self, game_state):
        # Try to play in column 1 if possible
        for move in game_state["possible_moves"]:
            if move.startswith("1"):
                return move
        # Fallback to first available move
        return game_state["possible_moves"][0]


@pytest.fixture
def test_league():
    """Create a test league for the game"""
    return League(
        name="test_league",
        game="lineup4"
    )


@pytest.fixture
def test_game(test_league):
    """Create a test game instance with test players"""
    game = Lineup4Game(test_league, verbose=True)
    # Clear default players and add our test players
    game.players = []
    game.players.append(TestRandomPlayer())
    game.players.append(TestColumnPlayer())
    game.scores = {str(player.name): 0 for player in game.players}
    return game


def test_game_initialization(test_league):
    """Test that the game initializes properly"""
    game = Lineup4Game(test_league)
    
    # Check initial state
    assert isinstance(game.board, dict)
    assert isinstance(game.move_history, list)
    assert isinstance(game.game_feedback, dict)
    assert isinstance(game.winning_sets, set)
    assert len(game.board) == 42  # 7 columns × 6 rows
    assert len(game.winning_sets) > 0
    
    # Check that board is initialized empty
    assert all(value is None for value in game.board.values())


def test_calculate_winning_sets(test_game):
    """Test the winning sets calculation"""
    winning_sets = test_game.calculate_winning_sets()
    
    # There should be:
    # - 24 horizontal winning sets (6 rows, 4 positions per row)
    # - 21 vertical winning sets (7 columns, 3 positions per column)
    # - 24 diagonal winning sets (12 rising, 12 falling)
    assert len(winning_sets) == 69
    
    # Test a few specific winning sets
    horizontal_set = ('1A', '2A', '3A', '4A')
    vertical_set = ('1A', '1B', '1C', '1D')
    rising_diagonal = ('1A', '2B', '3C', '4D')
    falling_diagonal = ('1D', '2C', '3B', '4A')
    
    assert horizontal_set in winning_sets
    assert vertical_set in winning_sets
    assert rising_diagonal in winning_sets
    assert falling_diagonal in winning_sets


def test_initialize_board(test_game):
    """Test board initialization"""
    test_game.initialize_board()
    
    # Check all 42 positions are initialized and empty
    assert len(test_game.board) == 42
    assert all(test_game.board[f"{col}{row}"] is None 
               for col in range(1, 8) 
               for row in string.ascii_uppercase[:6])
    
    # Check that move history is empty
    assert test_game.move_history == []


def test_get_possible_moves(test_game):
    """Test finding possible moves"""
    # Empty board should have 7 possible moves (one for each column)
    possible_moves = test_game.get_possible_moves()
    assert len(possible_moves) == 7
    
    # All should be bottom row positions
    assert all(move.endswith('A') for move in possible_moves)
    assert sorted(possible_moves) == ['1A', '2A', '3A', '4A', '5A', '6A', '7A']
    
    # Add some pieces and check possible moves
    test_game.make_move('1A', 'X')
    test_game.make_move('2A', 'O')
    
    possible_moves = test_game.get_possible_moves()
    assert '1A' not in possible_moves
    assert '2A' not in possible_moves
    assert '1B' in possible_moves
    assert '2B' in possible_moves


def test_make_move(test_game):
    """Test making a move on the board"""
    # Make a valid move
    result = test_game.make_move('1A', 'X')
    assert result is True
    assert test_game.board['1A'] == 'X'
    assert test_game.move_history == ['1A']
    
    # Make another valid move
    result = test_game.make_move('2A', 'O')
    assert result is True
    assert test_game.board['2A'] == 'O'
    assert test_game.move_history == ['1A', '2A']
    
    # Try an invalid move (already occupied)
    result = test_game.make_move('1A', 'O')
    assert result is False
    assert test_game.board['1A'] == 'X'  # Remains unchanged
    assert test_game.move_history == ['1A', '2A']  # Remains unchanged


def test_check_winner_horizontal(test_game):
    """Test detecting a horizontal win"""
    # Make moves for a horizontal win
    test_game.make_move('1A', 'X')
    test_game.make_move('2A', 'X')
    test_game.make_move('3A', 'X')
    
    # No winner yet
    assert test_game.check_winner() is False
    
    # Complete the winning line
    test_game.make_move('4A', 'X')
    
    # Now there should be a winner
    assert test_game.check_winner() is True


def test_check_winner_vertical(test_game):
    """Test detecting a vertical win"""
    # Make moves for a vertical win
    test_game.make_move('1A', 'X')
    test_game.make_move('1B', 'X')
    test_game.make_move('1C', 'X')
    
    # No winner yet
    assert test_game.check_winner() is False
    
    # Complete the winning line
    test_game.make_move('1D', 'X')
    
    # Now there should be a winner
    assert test_game.check_winner() is True


def test_check_winner_diagonal(test_game):
    """Test detecting a diagonal win"""
    # Set up a diagonal win scenario (rising diagonal)
    test_game.make_move('1A', 'X')
    test_game.make_move('2B', 'X')
    test_game.make_move('3C', 'X')
    
    # No winner yet
    assert test_game.check_winner() is False
    
    # Complete the winning line
    test_game.make_move('4D', 'X')
    
    # Now there should be a winner
    assert test_game.check_winner() is True
    
    # Reset and test falling diagonal
    test_game.initialize_board()
    
    test_game.make_move('1D', 'O')
    test_game.make_move('2C', 'O')
    test_game.make_move('3B', 'O')
    
    # No winner yet
    assert test_game.check_winner() is False
    
    # Complete the winning line
    test_game.make_move('4A', 'O')
    
    # Now there should be a winner
    assert test_game.check_winner() is True


def test_is_board_full(test_game):
    """Test detecting a full board"""
    # Empty board should not be full
    assert test_game.is_board_full() is False
    
    # Fill the board
    for col in range(1, 8):
        for row in string.ascii_uppercase[:6]:
            test_game.board[f"{col}{row}"] = 'X'
    
    # Now board should be full
    assert test_game.is_board_full() is True
    
    # Test partial fill
    test_game.initialize_board()
    for col in range(1, 8):
        for row in string.ascii_uppercase[:5]:  # Leave top row empty
            test_game.board[f"{col}{row}"] = 'X'
    
    # Board should not be full
    assert test_game.is_board_full() is False


def test_get_game_state(test_game):
    """Test getting the current game state"""
    # Make some moves
    test_game.make_move('1A', 'X')
    test_game.make_move('2A', 'O')
    
    # Get game state for a player
    player = test_game.players[0]
    state = test_game.get_game_state(player)
    
    # Check state structure
    assert "board" in state
    assert "possible_moves" in state
    assert "current_player" in state
    assert "last_move" in state
    assert "move_history" in state
    
    # Check specific values
    assert state["current_player"] == player.name
    assert state["last_move"] == '2A'
    assert state["move_history"] == ['1A', '2A']
    assert state["board"]['1A'] == 'X'
    assert state["board"]['2A'] == 'O'
    
    # Check possible moves are correct - pieces should stack
    assert '1B' in state["possible_moves"]  # Can play above existing piece at 1A
    assert '2B' in state["possible_moves"]  # Can play above existing piece at 2A
    # Rest of row A should be valid moves (columns 3-7)
    assert all(f"{col}A" in state["possible_moves"] for col in range(3, 8))


def test_play_match(test_game):
    """Test playing a single match between two players"""
    player1 = test_game.players[0]
    player2 = test_game.players[1]
    
    # Play a match
    match_result = test_game.play_match(player1, player2)
    
    # Check match result structure
    assert "player1" in match_result
    assert "player2" in match_result
    assert "moves" in match_result
    assert "winner" in match_result
    assert "final_board" in match_result
    
    # Check player assignments
    assert match_result["player1"] == player1.name
    assert match_result["player2"] == player2.name
    
    # Since both test players play deterministically, one should win
    assert match_result["winner"] in [player1.name, player2.name, "draw"]
    
    # Check moves were recorded
    assert len(match_result["moves"]) >= 7  # At least 7 moves for a win
    
    # Check final board is provided
    assert len(match_result["final_board"]) == 42


def test_play_game(test_game):
    """Test playing a complete game with multiple players"""
    # Play the game
    results = test_game.play_game()
    
    # Check results structure
    assert "points" in results
    assert "score_aggregate" in results
    assert "table" in results
    
    # Check that all players have scores
    for player in test_game.players:
        assert player.name in results["points"]
        assert player.name in results["score_aggregate"]
    
    # Check that game statistics are recorded
    assert "matches_played" in results["table"]
    assert "wins" in results["table"]
    assert "draws" in results["table"]
    
    # Check matches were played
    # Each pair plays twice (once with each player going first)
    expected_matches = len(test_game.players) * (len(test_game.players) - 1) * 2
    assert sum(results["table"]["matches_played"].values()) == expected_matches


def test_reset(test_game):
    """Test game reset functionality"""
    # Make some moves
    test_game.make_move('1A', 'X')
    test_game.make_move('2A', 'O')
    
    # Reset game
    test_game.reset()
    
    # Check that board was reset
    assert all(value is None for value in test_game.board.values())
    assert test_game.move_history == []
    assert test_game.game_feedback == {"game": "lineup4", "matches": []}


def test_run_simulations(test_game):
    """Test running multiple game simulations"""
    results = test_game.run_simulations(num_simulations=2, league=None)
    
    # Check results structure
    assert "total_points" in results
    assert "num_simulations" in results
    assert "table" in results
    
    # Check table contents
    assert "wins" in results["table"]
    assert "draws" in results["table"]
    assert "games_played" in results["table"]
    
    # Check that all players have scores
    for player in test_game.players:
        assert player.name in results["total_points"]
        assert player.name in results["table"]["wins"]
        assert player.name in results["table"]["draws"]
        assert player.name in results["table"]["games_played"]


def test_run_single_game_with_feedback(test_game):
    """Test running a single game with feedback enabled"""
    result = test_game.run_single_game_with_feedback()
    
    # Check structure of results
    assert "results" in result
    assert "feedback" in result
    assert "player_feedback" in result
    
    # Check feedback is properly structured
    assert result["feedback"]["game"] == "lineup4"
    assert "matches" in result["feedback"]
    assert "player_feedback" in result