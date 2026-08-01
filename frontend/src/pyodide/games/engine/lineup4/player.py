from abc import ABC, abstractmethod


class Player(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.feedback = []
        self.symbol = None  # 'X' or 'O'
        self.all_winning_sets = self.calculate_winning_sets()

    def add_feedback(self, message):
        """Add feedback that will be visible in the game output"""
        self.feedback.append(message)

    def calculate_winning_sets(self):
        all_winning_sets = set()

        # Horizontal winning sets
        for row in "ABCDEF":
            for col in range(1, 5):
                winning_set = tuple(f"{col+i}{row}" for i in range(4))
                all_winning_sets.add(winning_set)

        # Vertical winning sets
        for col in range(1, 8):
            for start_row in range(3):
                winning_set = tuple(f"{col}{'ABCDEF'[start_row+i]}" for i in range(4))
                all_winning_sets.add(winning_set)

        # Rising diagonal winning sets
        for col in range(1, 5):
            for row in range(3):
                winning_set = tuple(f"{col+i}{'ABCDEF'[row+i]}" for i in range(4))
                all_winning_sets.add(winning_set)

        # Falling diagonal winning sets
        for col in range(1, 5):
            for row in range(3, 6):
                winning_set = tuple(f"{col+i}{'ABCDEF'[row-i]}" for i in range(4))
                all_winning_sets.add(winning_set)

        return all_winning_sets

    @abstractmethod
    def make_decision(self, game_state):
        """
        Make a move decision based on the current game state.

        Args:
            game_state (dict): Contains:
                - board (dict): Current board state mapping positions (e.g. '1A') to symbols ('X', 'O', or None)
                - possible_moves (list): List of valid moves (e.g. ['1A', '1B', ...])
                - current_player (str): Name of the current player
                - last_move (str): The last move made, or None if first move
                - move_history (list): List of all moves made so far

        Returns:
            str: The chosen move (e.g. '1A')
        """
        pass
