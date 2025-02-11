import itertools
import random
import string

from backend.games.base_game import BaseGame


class Connect4Game(BaseGame):
    starter_code = """
from games.connect4.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # Available information in game_state:
        # - board: Dictionary mapping positions ('1A' to '7F') to symbols ('X', 'O', None)
        # - possible_moves: List of valid moves you can make
        # - current_player: Your player name
        # - last_move: The last move made
        # - move_history: List of all moves made so far
        
        # Simple example: Make a random valid move
        move = random.choice(game_state["possible_moves"])
        
        # Add custom feedback (will appear in game output)
        self.add_feedback(f"I chose move {move}")
        
        return move
"""

    game_instructions = """
    <h1>Connect 4 Game Instructions</h1>
    
    <p>Implement a Connect 4 player by creating a strategy for choosing moves on a 7x6 grid.</p>
    
    <h2>Board Layout</h2>
    <ul>
        <li>The board is 7 columns wide (numbered 1-7) and 6 rows high (lettered A-F)</li>
        <li>Positions are referenced by column then row (e.g., '1A' is bottom-left, '7F' is top-right)</li>
        <li>Pieces stack from the bottom up (like real Connect 4)</li>
    </ul>
    
    <h2>Game Rules</h2>
    <ul>
        <li>Players alternate placing pieces</li>
        <li>First player to connect 4 pieces horizontally, vertically, or diagonally wins</li>
        <li>If the board fills up with no winner, the game is a draw</li>
    </ul>
    
    <h2>Implementation Notes</h2>
    <ul>
        <li>Your make_decision method receives the full game state including valid moves</li>
        <li>You can use random.choice(game_state["possible_moves"]) for a valid random move</li>
        <li>Add feedback with self.add_feedback() to help debug your strategy</li>
    </ul>
    """

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.board = {}
        self.move_history = []
        self.game_feedback = {"game": "connect4", "matches": []}
        self.initialize_board()

    def initialize_board(self):
        """Set up an empty board"""
        self.board = {}
        for col in range(1, 8):  # 7 columns
            for row in string.ascii_uppercase[:6]:  # 6 rows A-F
                self.board[f"{col}{row}"] = None
        self.move_history = []

    def get_possible_moves(self):
        """Get list of valid moves"""
        possible_moves = []
        for col in range(1, 8):
            # Check each column from bottom up
            for row in string.ascii_uppercase[:6]:
                pos = f"{col}{row}"
                if self.board[pos] is None:
                    possible_moves.append(pos)
                    break  # Only the lowest empty position in each column is valid
        return possible_moves

    def make_move(self, position, symbol):
        """Make a move on the board"""
        if position in self.board and self.board[position] is None:
            self.board[position] = symbol
            self.move_history.append(position)
            return True
        return False

    def check_winner(self):
        """Check if anyone has won"""
        # Check horizontal
        for row in string.ascii_uppercase[:6]:
            for col in range(1, 5):  # Only need to check starting positions
                positions = [f"{col+i}{row}" for i in range(4)]
                if self._check_line(positions):
                    return True

        # Check vertical
        for col in range(1, 8):
            for row_idx in range(3):  # Only need to check bottom 3 starting positions
                positions = [
                    f"{col}{string.ascii_uppercase[row_idx+i]}" for i in range(4)
                ]
                if self._check_line(positions):
                    return True

        # Check diagonal (rising)
        for col in range(1, 5):
            for row_idx in range(3):  # Bottom 3 rows
                positions = [
                    f"{col+i}{string.ascii_uppercase[row_idx+i]}" for i in range(4)
                ]
                if self._check_line(positions):
                    return True

        # Check diagonal (falling)
        for col in range(1, 5):
            for row_idx in range(3, 6):  # Top 3 rows
                positions = [
                    f"{col+i}{string.ascii_uppercase[row_idx-i]}" for i in range(4)
                ]
                if self._check_line(positions):
                    return True

        return False

    def _check_line(self, positions):
        """Check if a line of positions contains four matching symbols"""
        first = self.board[positions[0]]
        if first is None:
            return False
        return all(self.board[pos] == first for pos in positions)

    def is_board_full(self):
        """Check if the board is full"""
        return all(self.board[pos] is not None for pos in self.board)

    def get_game_state(self, current_player):
        """Get the current game state"""
        return {
            "board": dict(self.board),
            "possible_moves": self.get_possible_moves(),
            "current_player": str(current_player.name),
            "last_move": self.move_history[-1] if self.move_history else None,
            "move_history": list(self.move_history),
        }

    def play_match(self, player1, player2):
        """Play a single match between two players"""
        self.initialize_board()
        match_feedback = {
            "player1": str(player1.name),
            "player2": str(player2.name),
            "moves": [],
            "winner": None,
            "final_board": None,
        }

        # Assign symbols
        player1.symbol = "X"
        player2.symbol = "O"

        current_player = player1
        other_player = player2

        while True:
            game_state = self.get_game_state(current_player)

            try:
                move = current_player.make_decision(game_state)
            except Exception as e:
                if self.verbose:
                    match_feedback["moves"].append(
                        f"Error in player {current_player.name}'s move: {e}"
                    )
                move = self.get_possible_moves()[0]  # Make a valid move

            # Record the move
            move_data = {
                "player": str(current_player.name),
                "symbol": current_player.symbol,
                "position": move,
                "board_state": dict(self.board),
            }
            match_feedback["moves"].append(move_data)

            # Make the move
            if not self.make_move(move, current_player.symbol):
                if self.verbose:
                    match_feedback["moves"].append(
                        f"Invalid move by {current_player.name}: {move}"
                    )
                continue

            # Add any player feedback
            if current_player.feedback:
                if str(current_player.name) not in self.player_feedback:
                    self.player_feedback[str(current_player.name)] = []
                self.player_feedback[str(current_player.name)].extend(
                    current_player.feedback
                )
                current_player.feedback = []

            # Check for winner
            if self.check_winner():
                match_feedback["winner"] = str(current_player.name)
                break

            # Check for draw
            if self.is_board_full():
                match_feedback["winner"] = "draw"
                break

            # Switch players
            current_player, other_player = other_player, current_player

        # Record final board state
        match_feedback["final_board"] = dict(self.board)

        return match_feedback

    def play_game(self, custom_rewards=None):
        """Play a complete game (round-robin tournament)"""
        self.game_feedback = {"game": "connect4", "matches": []}
        self.player_feedback = {}

        # Create all possible pairs of players
        player_pairs = list(itertools.combinations(self.players, 2))
        random.shuffle(player_pairs)  # Randomize order of matches

        # Initialize scores
        scores = {str(player.name): 0 for player in self.players}

        # Play each match
        for player1, player2 in player_pairs:
            # Each pair plays twice, alternating who goes first
            for first, second in [(player1, player2), (player2, player1)]:
                match_result = self.play_match(first, second)
                if self.verbose:
                    self.game_feedback["matches"].append(match_result)

                # Award points
                if match_result["winner"] == str(first.name):
                    scores[str(first.name)] += 1
                elif match_result["winner"] == str(second.name):
                    scores[str(second.name)] += 1
                # No points for draws

        return {
            "points": scores,
            "score_aggregate": dict(scores),
            "table": {"matches_played": len(player_pairs) * 2},
        }

    def run_simulations(self, num_simulations, league, custom_rewards=None):
        """Run multiple simulations"""
        multiplier_round_robin = 1
        num_players = len(self.players)
        if num_players > 1:
            multiplier_round_robin = num_players * (num_players - 1)
        if multiplier_round_robin * num_simulations > 1000:
            num_simulations = 1000 // multiplier_round_robin
        if num_simulations < 2:
            num_simulations = 2

        total_points = {str(player.name): 0 for player in self.players}
        wins = {str(player.name): 0 for player in self.players}
        draws = 0

        for _ in range(num_simulations):
            self.reset()
            results = self.play_game(custom_rewards)

            # Update total points
            for player, points in results["points"].items():
                total_points[str(player)] += points
                wins[str(player)] += points  # In this case, points = wins

        return {
            "total_points": total_points,
            "num_simulations": num_simulations * multiplier_round_robin,
            "table": {"wins": wins, "draws": draws},
        }

    def reset(self):
        """Reset game state"""
        super().reset()  # Call base class reset
        self.board = {}  # Clear the board
        self.initialize_board()  # Reinitialize with empty positions
        self.move_history = []  # Explicitly clear move history
        self.game_feedback = {"game": "connect4", "matches": []}
