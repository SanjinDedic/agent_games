import random

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


# List of players to be used for validation games
players = [RandomPlayer(), LeftStackPlayer()]
