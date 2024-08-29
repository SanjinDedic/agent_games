from abc import ABC, abstractmethod

class Player(ABC):
    def __init__(self):
        self.name = None

    @abstractmethod
    def make_decision(self, game_state):
        pass