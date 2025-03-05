import random
import string

from backend.games.lineup4.player import Player


class RandomPlayer(Player):
    """Player that makes random valid moves"""

    def make_decision(self, game_state):
        move = random.choice(game_state["possible_moves"])
        self.add_feedback(f"Randomly chose move: {move}")
        return move


class LeftStackPlayer(Player):
    """Player that always plays in the leftmost available column"""

    def make_decision(self, game_state):
        # Group possible moves by column
        moves_by_column = {}
        for move in game_state["possible_moves"]:
            col = move[0]  # First character is the column number
            if col not in moves_by_column:
                moves_by_column[col] = []
            moves_by_column[col].append(move)

        # Find the leftmost column that has available moves
        for col in sorted(moves_by_column.keys()):
            if moves_by_column[col]:
                # Take the lowest available position in this column
                # (moves are ordered like '1A', '1B', etc. where A is bottom)
                move = sorted(moves_by_column[col])[0]
                self.add_feedback(f"Playing in leftmost column {col}, position {move}")
                return move

        # Fallback to random move if something goes wrong
        return random.choice(game_state["possible_moves"])


class MrCenter(Player):
    """Player that always plays in the leftmost available column"""

    def make_decision(self, game_state):
        preferred_columns = [4, 3, 5, 2, 6, 1, 7]
        for preferred_col in preferred_columns:
            for move in game_state["possible_moves"]:
                col = int(move[0])  # First character is the column number
                if col == preferred_col:
                    return move
        return random.choice(game_state["possible_moves"])


class RandomUntilWin(Player):
    def check_potential_win(self, board: dict, move: str, symbol: str) -> bool:
        """Check if making this move would create a win"""
        # Temporarily make the move
        original = board[move]
        board[move] = symbol

        # Check all winning sets that include this position
        for winning_set in self.all_winning_sets:
            if move in winning_set:
                if all(board[pos] == symbol for pos in winning_set):
                    board[move] = original
                    return True

        # Reset the board and return
        board[move] = original
        return False

    def make_decision(self, game_state):
        board = game_state["board"]
        possible_moves = game_state["possible_moves"]
        # Win if possible
        for move in possible_moves:
            if self.check_potential_win(board, move, self.symbol):
                self.add_feedback(f"Winning move: {move}")
                return move

        return random.choice(game_state["possible_moves"])


class BlockUntilWin(Player):
    """Smart Lineup4 player that prioritizes wins and blocking."""

    def check_potential_win(self, board: dict, move: str, symbol: str) -> bool:
        """Check if making this move would create a win"""
        # Temporarily make the move
        original = board[move]
        board[move] = symbol

        # Check all winning sets that include this position
        for winning_set in self.all_winning_sets:
            if move in winning_set:
                if all(board[pos] == symbol for pos in winning_set):
                    board[move] = original
                    return True

        # Reset the board and return
        board[move] = original
        return False

    def make_decision(self, game_state):
        board = game_state["board"]
        possible_moves = game_state["possible_moves"]

        # First priority: Win if possible
        for move in possible_moves:
            if self.check_potential_win(board, move, self.symbol):
                self.add_feedback(f"Winning move: {move}")
                return move

        # Second priority: Block opponent wins
        opponent_symbol = "O" if self.symbol == "X" else "X"
        for move in possible_moves:
            if self.check_potential_win(board, move, opponent_symbol):
                self.add_feedback(f"Blocking opponent at: {move}")
                return move

        return random.choice(game_state["possible_moves"])


# List of players to be used for validation games
players = [
    RandomPlayer(),
    LeftStackPlayer(),
    RandomUntilWin(),
    MrCenter(),
    BlockUntilWin(),
]
