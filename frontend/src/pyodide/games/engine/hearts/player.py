from abc import ABC, abstractmethod


class Player(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.feedback = []

    def add_feedback(self, message):
        """Add feedback that will be visible in the game output"""
        self.feedback.append(message)

    @abstractmethod
    def make_decision(self, game_state):
        """Called for both phases of a Hearts hand.

        game_state["phase"] == "pass": return a list of exactly 3 card codes
        from game_state["hand"] to pass to the next player.

        game_state["phase"] == "play": return one card code from
        game_state["legal_moves"].

        Card codes are rank + suit letter, e.g. "QS", "10H", "2C".
        """
        pass
