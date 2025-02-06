from abc import ABC, abstractmethod


class Player(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.feedback = []
        self.symbol = None  # 'X' or 'O'

    def add_feedback(self, message):
        """Add feedback that will be visible in the game output"""
        self.feedback.append(message)

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
