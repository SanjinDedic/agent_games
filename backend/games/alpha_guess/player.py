from abc import ABC, abstractmethod

class Player(ABC):
    @abstractmethod
    def make_decision(self, game_state):
        pass