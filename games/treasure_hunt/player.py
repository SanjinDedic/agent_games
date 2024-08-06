from abc import ABC, abstractmethod

class Player(ABC):
    def __init__(self):
        self.name = ''
        self.position = (0, 0)

    @abstractmethod
    def make_decision(self, game_state):
        pass
