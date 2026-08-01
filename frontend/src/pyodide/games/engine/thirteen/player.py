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
        """Called once for every turn of Thirteen (Tiến lên).

        Return **one combination** — a list of card codes — chosen from
        game_state["legal_moves"], or the empty list [] to pass.

        - When game_state["leading"] is True you must start a fresh pile: every
          entry in legal_moves is a non-empty combo and passing is not allowed.
        - Otherwise you are answering game_state["pile"]: legal_moves holds every
          combo that beats it (same shape + length, strictly higher — or a
          four-of-a-kind bomb over a single/pair of 2s or a lower bomb), plus the
          empty list [] which means pass.

        Card codes are rank + suit letter, e.g. "3S", "10H", "2C". In Thirteen 3
        is the lowest rank and 2 is the highest; suits rank S < C < D < H.
        """
        pass
