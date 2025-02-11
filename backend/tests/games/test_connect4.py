from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import League, Team
from backend.games.connect4.connect4 import Connect4Game
from backend.games.connect4.player import Player


@pytest.fixture
def test_league():
    return League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="connect4",
    )


def test_game_initialization(test_league):
    """Test basic initialization of Connect4Game"""
    game = Connect4Game(test_league)
    assert len(game.players) > 0  # Should have validation players
    # Board should be initialized with empty positions
    assert all(value is None for value in game.board.values())
    assert len(game.board) == 42  # 7x6 board
    assert game.move_history == []
    assert game.game_feedback == {"game": "connect4", "matches": []}


def test_board_initialization(test_league):
    """Test board initialization"""
    game = Connect4Game(test_league)
    game.initialize_board()

    # Verify board dimensions (7x6)
    assert len(game.board) == 42  # 7 columns x 6 rows

    # Verify all positions are empty
    assert all(value is None for value in game.board.values())

    # Verify correct position naming (1A to 7F)
    expected_positions = [f"{col}{row}" for col in range(1, 8) for row in "ABCDEF"]
    assert sorted(game.board.keys()) == sorted(expected_positions)


def test_get_possible_moves(test_league):
    """Test possible moves calculation"""
    game = Connect4Game(test_league)
    game.initialize_board()

    # Initially, only bottom row should be available
    initial_moves = game.get_possible_moves()
    assert sorted(initial_moves) == ["1A", "2A", "3A", "4A", "5A", "6A", "7A"]

    # Make a move and verify next possible moves
    game.make_move("1A", "X")
    new_moves = game.get_possible_moves()
    assert "1B" in new_moves  # Position above 1A should now be available
    assert "1A" not in new_moves  # 1A should no longer be available


def test_make_move(test_league):
    """Test move execution"""
    game = Connect4Game(test_league)
    game.initialize_board()

    # Test valid move
    assert game.make_move("1A", "X") is True
    assert game.board["1A"] == "X"
    assert game.move_history == ["1A"]

    # Test invalid moves
    assert game.make_move("1A", "O") is False  # Already occupied
    assert game.make_move("8A", "X") is False  # Invalid position
    assert game.make_move("1G", "X") is False  # Invalid position


def test_check_winner(test_league):
    """Test win condition detection"""
    game = Connect4Game(test_league)
    game.initialize_board()

    # Test horizontal win
    for col in range(1, 5):
        game.make_move(f"{col}A", "X")
    assert game.check_winner() is True

    # Reset and test vertical win
    game.initialize_board()
    for row in "ABCD":
        game.make_move(f"1{row}", "X")
    assert game.check_winner() is True

    # Reset and test diagonal win (rising)
    game.initialize_board()
    game.make_move("1A", "X")
    game.make_move("2B", "X")
    game.make_move("3C", "X")
    game.make_move("4D", "X")
    assert game.check_winner() is True

    # Reset and test diagonal win (falling)
    game.initialize_board()
    game.make_move("4A", "X")
    game.make_move("3B", "X")
    game.make_move("2C", "X")
    game.make_move("1D", "X")
    assert game.check_winner() is True


def test_is_board_full(test_league):
    """Test board full condition"""
    game = Connect4Game(test_league)
    game.initialize_board()

    assert game.is_board_full() is False

    # Fill entire board
    for col in range(1, 8):
        for row in "ABCDEF":
            game.make_move(f"{col}{row}", "X")

    assert game.is_board_full() is True


def test_get_game_state(test_league):
    """Test game state retrieval"""
    game = Connect4Game(test_league)
    game.initialize_board()

    # Create test players
    class TestPlayer(Player):
        def make_decision(self, game_state):
            return game_state["possible_moves"][0]

    player = TestPlayer()
    player.name = "TestPlayer"

    # Make some moves
    game.make_move("1A", "X")
    game.make_move("2A", "O")

    # Get game state
    state = game.get_game_state(player)

    assert "board" in state
    assert "possible_moves" in state
    assert "current_player" in state
    assert "last_move" in state
    assert "move_history" in state
    assert state["current_player"] == "TestPlayer"
    assert state["last_move"] == "2A"
    assert len(state["move_history"]) == 2


def test_play_match(test_league):
    """Test complete match execution"""
    game = Connect4Game(test_league)

    # Use validation players
    player1, player2 = game.players[:2]

    # Play match
    match_feedback = game.play_match(player1, player2)

    assert "player1" in match_feedback
    assert "player2" in match_feedback
    assert "moves" in match_feedback
    assert "winner" in match_feedback
    assert "final_board" in match_feedback
    assert isinstance(match_feedback["moves"], list)
    assert all(isinstance(move, dict) for move in match_feedback["moves"])


def test_play_game(test_league):
    """Test complete game execution"""
    game = Connect4Game(test_league)
    results = game.play_game()

    assert "points" in results
    assert "score_aggregate" in results
    assert isinstance(results["points"], dict)
    assert isinstance(results["score_aggregate"], dict)
    assert "table" in results
    assert "matches_played" in results["table"]


def test_run_simulations(test_league):
    """Test multiple simulation runs"""
    game = Connect4Game(test_league)
    num_simulations = 10
    results = game.run_simulations(num_simulations, test_league)

    assert "total_points" in results
    assert "num_simulations" in results
    assert results["num_simulations"] == num_simulations * (
        len(game.players) * (len(game.players) - 1)
    )
    assert "table" in results
    assert "wins" in results["table"]
    assert "draws" in results["table"]


def test_player_decision_exception(test_league):
    """Test handling of player decision exceptions"""
    game = Connect4Game(test_league)
    game.initialize_board()
    player1, player2 = game.players[:2]

    # Mock player1's make_decision method to raise exception
    def mock_decision(game_state):
        raise Exception("Test exception")

    player1.make_decision = mock_decision

    # Play match and verify exception is handled gracefully
    match_feedback = game.play_match(player1, player2)

    # Game should complete despite the exception
    assert match_feedback["winner"] is not None
    assert len(match_feedback["moves"]) > 0
    # First move should be valid despite the exception
    first_move = match_feedback["moves"][0]["position"]
    assert first_move in ["1A", "2A", "3A", "4A", "5A", "6A", "7A"]


def test_starter_code():
    """Test starter code content"""
    assert "class CustomPlayer(Player):" in Connect4Game.starter_code
    assert "def make_decision(self, game_state):" in Connect4Game.starter_code
    assert 'game_state["possible_moves"]' in Connect4Game.starter_code


def test_game_instructions():
    """Test game instructions content"""
    assert "Connect 4 Game Instructions" in Connect4Game.game_instructions
    assert "Board Layout" in Connect4Game.game_instructions
    assert "Game Rules" in Connect4Game.game_instructions
    assert "Implementation Notes" in Connect4Game.game_instructions


def test_game_reset(test_league):
    """Test game state reset"""
    game = Connect4Game(test_league)

    # Make some moves
    game.initialize_board()
    game.make_move("1A", "X")
    game.make_move("2A", "O")

    # Reset game
    game.reset()

    # Verify board is in initial state
    assert len(game.board) == 42  # Should have all positions
    assert game.move_history == []
    assert game.game_feedback == {"game": "connect4", "matches": []}
    # Verify some specific positions are empty
    assert game.board["1A"] is None
    assert game.board["2A"] is None
