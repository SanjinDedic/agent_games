import random
import string

from backend.games.connect4.player import Player


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
    """Player that checks for winning moves but otherwise plays randomly"""

    def is_valid_position(self, col: int, row_position: int) -> bool:
        """Check if a board position is valid"""
        return 1 <= col <= 7 and 0 <= row_position < 6

    def check_win(self, board: dict, pos: str, symbol: str) -> bool:
        """Check if placing symbol at pos would create a win"""
        # Save original board state
        original_value = board[pos]
        board[pos] = symbol

        # Get position coordinates
        column = int(pos[0])  # First char is column number (1-7)
        row_letter = pos[1]  # Second char is row letter (A-F)
        row_position = string.ascii_uppercase.index(
            row_letter
        )  # Convert letter to number (A=0, B=1, etc)

        # Check all possible win directions
        has_win = (
            self.check_horizontal_win(board, column, row_letter, symbol)
            or self.check_vertical_win(board, column, row_position, symbol)
            or self.check_rising_diagonal_win(board, column, row_position, symbol)
            or self.check_falling_diagonal_win(board, column, row_position, symbol)
        )

        # Restore original board state
        board[pos] = original_value
        return has_win

    def check_horizontal_win(
        self, board: dict, col: int, row_letter: str, symbol: str
    ) -> bool:
        """Check for 4 in a row horizontally"""
        # For each possible starting column that could contain a win
        for start_col in range(max(1, col - 3), min(5, col + 1)):
            # Create list of 4 consecutive positions
            positions = [f"{start_col+i}{row_letter}" for i in range(4)]
            if all(board[p] == symbol for p in positions):
                return True
        return False

    def check_vertical_win(
        self, board: dict, col: int, row_position: int, symbol: str
    ) -> bool:
        """Check for 4 in a row vertically"""
        # For each possible starting row that could contain a win
        for start_row in range(max(0, row_position - 3), min(3, row_position + 1)):
            # Create list of 4 consecutive positions
            positions = [
                f"{col}{string.ascii_uppercase[start_row+i]}" for i in range(4)
            ]
            if all(board[p] == symbol for p in positions):
                return True
        return False

    def check_rising_diagonal_win(
        self, board: dict, col: int, row_position: int, symbol: str
    ) -> bool:
        """Check for 4 in a row diagonally rising (bottom-left to top-right)"""
        # Check all possible 4-piece diagonals that could contain this position
        for i in range(4):
            # Calculate potential diagonal coordinates
            start_col = col - i
            start_row = row_position - i
            end_col = start_col + 3
            end_row = start_row + 3

            # Check if this diagonal fits on the board
            if self.is_valid_position(start_col, start_row) and self.is_valid_position(
                end_col, end_row
            ):
                # Create list of 4 diagonal positions
                positions = [
                    f"{start_col+j}{string.ascii_uppercase[start_row+j]}"
                    for j in range(4)
                ]
                if all(board[p] == symbol for p in positions):
                    return True
        return False

    def check_falling_diagonal_win(
        self, board: dict, col: int, row_position: int, symbol: str
    ) -> bool:
        """Check for 4 in a row diagonally falling (top-left to bottom-right)"""
        # Check all possible 4-piece diagonals that could contain this position
        for i in range(4):
            # Calculate potential diagonal coordinates
            start_col = col - i
            start_row = row_position + i
            end_col = start_col + 3
            end_row = start_row - 3

            # Check if this diagonal fits on the board
            if self.is_valid_position(start_col, start_row) and self.is_valid_position(
                end_col, end_row
            ):
                # Create list of 4 diagonal positions
                positions = [
                    f"{start_col+j}{string.ascii_uppercase[start_row-j]}"
                    for j in range(4)
                ]
                if all(board[p] == symbol for p in positions):
                    return True
        return False

    def make_decision(self, game_state):
        board = game_state["board"]
        possible_moves = game_state["possible_moves"]

        # First check if any move gives us a win
        for move in possible_moves:
            if self.check_win(board, move, self.symbol):
                self.add_feedback(f"Found winning move: {move}")
                return move

        # If no winning move, play randomly
        move = random.choice(possible_moves)
        self.add_feedback(f"No winning move found, playing randomly: {move}")
        return move


class BlockUntilWin(Player):
    """Smart Connect4 player that prioritizes wins and blocking."""

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
