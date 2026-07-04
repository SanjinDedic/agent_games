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
        """Called for both phases of an Oh Hell round.

        game_state["phase"] == "bid": return an integer between 0 and
        game_state["cards_this_round"] — how many tricks you promise to take.
        If you are the last player to bid, game_state["forbidden_bid"] is the
        one value you are not allowed to bid (it would make everyone's bids add
        up to the number of tricks).

        game_state["phase"] == "play": return one card code from
        game_state["legal_moves"].

        Card codes are rank + suit letter, e.g. "QS", "10H", "2C".
        """
        pass
