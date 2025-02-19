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
        # - last_move: The last move made by your opponent

        # Other available information:
        # - self.symbol tells you whether you are 'X' or 'O'
           
        # Add custom feedback (will appear in game output)
        self.add_feedback("Everything you write here you will see in the game output")
        
        return random.choice(game_state["possible_moves"]) # fallback to random move
"""

    game_instructions = """
# Connect 4 Game Instructions

Implement a Connect 4 player by creating a strategy for choosing moves on a 7x6 grid.

## Board Layout
- The board is 7 columns wide (numbered 1-7) and 6 rows high (lettered A-F)
- Positions are referenced by column then row (e.g., '1A' is bottom-left, '7F' is top-right)
- Pieces stack from the bottom up (like real Connect 4)

## Game Rules
- Players alternate placing pieces
- First player to connect 4 pieces horizontally, vertically, or diagonally wins
- If the board fills up with no winner, the game is a draw

## Implementation Notes
- Your make_decision method receives the full game state including valid moves
- You can use random.choice(game_state["possible_moves"]) for a valid random move
- Add feedback with self.add_feedback() to help debug your strategy
    """

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.board = {}
        self.move_history = []
        self.game_feedback = {"game": "connect4", "matches": []}
        self.winning_sets = self.calculate_winning_sets()  # Pre-calculate winning sets
        self.initialize_board()

    def calculate_winning_sets(self):
        """Calculate all possible winning combinations"""
        all_winning_sets = set()

        # Horizontal winning sets
        for row in string.ascii_uppercase[:6]:
            for col in range(1, 5):
                winning_set = tuple(f"{col+i}{row}" for i in range(4))
                all_winning_sets.add(winning_set)

        # Vertical winning sets
        for col in range(1, 8):
            for start_row in range(3):
                winning_set = tuple(
                    f"{col}{string.ascii_uppercase[start_row+i]}" for i in range(4)
                )
                all_winning_sets.add(winning_set)

        # Rising diagonal winning sets
        for col in range(1, 5):
            for row in range(3):
                winning_set = tuple(
                    f"{col+i}{string.ascii_uppercase[row+i]}" for i in range(4)
                )
                all_winning_sets.add(winning_set)

        # Falling diagonal winning sets
        for col in range(1, 5):
            for row in range(3, 6):
                winning_set = tuple(
                    f"{col+i}{string.ascii_uppercase[row-i]}" for i in range(4)
                )
                all_winning_sets.add(winning_set)

        return all_winning_sets

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
        """Check if anyone has won using pre-calculated winning sets"""
        # Get last move if available
        last_move = self.move_history[-1] if self.move_history else None
        if not last_move:
            return False

        # Get the symbol at the last move
        last_symbol = self.board[last_move]

        # Only check winning sets that include the last move made
        for winning_set in self.winning_sets:
            if last_move in winning_set:
                if all(self.board[pos] == last_symbol for pos in winning_set):
                    return True

        return False

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
                if move not in game_state["possible_moves"]:
                    raise ValueError(
                        f"Invalid move {move} - must be one of {game_state['possible_moves']}"
                    )
            except Exception as e:
                raise ValueError(f"Invalid move by {current_player.name}: {str(e)}")

            # Record the move
            move_data = {
                "player": str(current_player.name),
                "symbol": current_player.symbol,
                "position": move,
                "player_feedback": current_player.feedback,
                "board_state": dict(self.board),
            }
            match_feedback["moves"].append(move_data)
            current_player.feedback = []  # Clear feedback

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

            # Check for draw - board is full with no winner
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

        # Initialize scores and statistics
        scores = {str(player.name): 0 for player in self.players}
        wins = {str(player.name): 0 for player in self.players}
        draws = {str(player.name): 0 for player in self.players}
        matches_played = {str(player.name): 0 for player in self.players}
        total_draws = 0

        # Play each match
        for player1, player2 in player_pairs:
            # Each pair plays twice, alternating who goes first
            for first, second in [(player1, player2), (player2, player1)]:
                match_result = self.play_match(first, second)

                # Track matches played for both players
                matches_played[str(first.name)] += 1
                matches_played[str(second.name)] += 1

                if self.verbose:
                    self.game_feedback["matches"].append(match_result)

                # Award points - 2 points for win, 1 point for draw
                if match_result["winner"] == str(first.name):
                    scores[str(first.name)] += 2
                    wins[str(first.name)] += 1
                elif match_result["winner"] == str(second.name):
                    scores[str(second.name)] += 2
                    wins[str(second.name)] += 1
                elif match_result["winner"] == "draw":
                    scores[str(first.name)] += 1
                    scores[str(second.name)] += 1
                    draws[str(first.name)] += 1
                    draws[str(second.name)] += 1
                    total_draws += 1

        # Prepare game statistics
        stats = {
            "matches_played": matches_played,
            "wins": wins,
            "draws": draws,
            "total_draws": total_draws,
        }

        return {
            "points": scores,
            "score_aggregate": dict(scores),
            "table": stats,
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

        # Initialize counters
        total_points = {str(player.name): 0 for player in self.players}
        total_wins = {str(player.name): 0 for player in self.players}
        total_draws = {str(player.name): 0 for player in self.players}
        total_games_played = {str(player.name): 0 for player in self.players}

        for _ in range(num_simulations):
            self.reset()
            results = self.play_game(custom_rewards)

            # Accumulate points
            for player, points in results["points"].items():
                total_points[str(player)] += points

            # Accumulate statistics
            for player, wins in results["table"]["wins"].items():
                total_wins[str(player)] += wins

            for player, draws in results["table"]["draws"].items():
                total_draws[str(player)] += draws

            for player, games in results["table"]["matches_played"].items():
                total_games_played[str(player)] += games

        # Calculate actual total games played across all simulations
        actual_games_played = sum(total_games_played.values()) // 2

        return {
            "total_points": total_points,
            "num_simulations": actual_games_played,
            "table": {
                "wins": total_wins,
                "draws": total_draws,
                "games_played": total_games_played,
            },
        }

    def reset(self):
        """Reset game state"""
        super().reset()  # Call base class reset
        self.board = {}  # Clear the board
        self.initialize_board()  # Reinitialize with empty positions
        self.move_history = []  # Explicitly clear move history
        self.game_feedback = {"game": "connect4", "matches": []}

    def run_single_game_with_feedback(self, custom_rewards=None):
        """Run a single game with feedback"""
        self.verbose = True
        self.collect_player_feedback = True

        # Run the game
        results = self.play_game(custom_rewards)

        return {
            "results": results,
            "feedback": self.game_feedback,
            "player_feedback": self.player_feedback,
        }
