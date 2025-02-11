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


class RandomUntilWin(Player):
    """Player that checks for winning moves but otherwise plays randomly"""

    def check_win(self, board: dict, pos: str, symbol: str) -> bool:
        """Check if placing symbol at pos would create a win"""
        # Store original value
        original = board[pos]
        # Temporarily place our symbol
        board[pos] = symbol

        # Check horizontal
        col = int(pos[0])
        row = pos[1]
        for start_col in range(max(1, col - 3), min(5, col + 1)):
            positions = [f"{start_col+i}{row}" for i in range(4)]
            if all(board[p] == symbol for p in positions):
                board[pos] = original
                return True

        # Check vertical
        row_idx = string.ascii_uppercase.index(row)
        for start_row in range(max(0, row_idx - 3), min(3, row_idx + 1)):
            positions = [
                f"{col}{string.ascii_uppercase[start_row+i]}" for i in range(4)
            ]
            if all(board[p] == symbol for p in positions):
                board[pos] = original
                return True

        # Check diagonal (rising)
        for i in range(4):
            if (
                col - i >= 1
                and col - i + 3 <= 7
                and row_idx - i >= 0
                and row_idx - i + 3 < 6
            ):
                positions = [
                    f"{col-i+j}{string.ascii_uppercase[row_idx-i+j]}" for j in range(4)
                ]
                if all(board[p] == symbol for p in positions):
                    board[pos] = original
                    return True

        # Check diagonal (falling)
        for i in range(4):
            if (
                col - i >= 1
                and col - i + 3 <= 7
                and row_idx + i < 6
                and row_idx + i - 3 >= 0
            ):
                positions = [
                    f"{col-i+j}{string.ascii_uppercase[row_idx+i-j]}" for j in range(4)
                ]
                if all(board[p] == symbol for p in positions):
                    board[pos] = original
                    return True

        # Reset the board
        board[pos] = original
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


class Blocker(Player):
    """Player that blocks opponent wins and plays randomly otherwise"""

    def check_win(self, board: dict, pos: str, symbol: str) -> bool:
        """Check if placing symbol at pos would create a win"""
        # Store original value
        original = board[pos]
        # Temporarily place our symbol
        board[pos] = symbol

        # Check horizontal
        col = int(pos[0])
        row = pos[1]
        for start_col in range(max(1, col - 3), min(5, col + 1)):
            positions = [f"{start_col+i}{row}" for i in range(4)]
            if all(board[p] == symbol for p in positions):
                board[pos] = original
                return True

        # Check vertical
        row_idx = string.ascii_uppercase.index(row)
        for start_row in range(max(0, row_idx - 3), min(3, row_idx + 1)):
            positions = [
                f"{col}{string.ascii_uppercase[start_row+i]}" for i in range(4)
            ]
            if all(board[p] == symbol for p in positions):
                board[pos] = original
                return True

        # Check diagonal (rising)
        for i in range(4):
            if (
                col - i >= 1
                and col - i + 3 <= 7
                and row_idx - i >= 0
                and row_idx - i + 3 < 6
            ):
                positions = [
                    f"{col-i+j}{string.ascii_uppercase[row_idx-i+j]}" for j in range(4)
                ]
                if all(board[p] == symbol for p in positions):
                    board[pos] = original
                    return True

        # Check diagonal (falling)
        for i in range(4):
            if (
                col - i >= 1
                and col - i + 3 <= 7
                and row_idx + i < 6
                and row_idx + i - 3 >= 0
            ):
                positions = [
                    f"{col-i+j}{string.ascii_uppercase[row_idx+i-j]}" for j in range(4)
                ]
                if all(board[p] == symbol for p in positions):
                    board[pos] = original
                    return True

        # Reset the board
        board[pos] = original
        return False

    def make_decision(self, game_state):
        board = game_state["board"]
        possible_moves = game_state["possible_moves"]
        opponent_symbol = "O" if self.symbol == "X" else "X"

        # Then check if we need to block opponent
        for move in possible_moves:
            if self.check_win(board, move, opponent_symbol):
                self.add_feedback(f"Blocking opponent win at: {move}")
                return move

        # If no winning or blocking moves, play randomly
        move = random.choice(possible_moves)
        self.add_feedback(
            f"No winning or blocking moves found, playing randomly: {move}"
        )
        return move


# List of players to be used for validation games
players = [RandomPlayer(), LeftStackPlayer(), RandomUntilWin(), Blocker()]
