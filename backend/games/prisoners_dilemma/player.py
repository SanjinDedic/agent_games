from abc import ABC, abstractmethod

class Player(ABC):
    def __init__(self):
        self.name = None
        self.feedback = []

    @abstractmethod
    def make_decision(self, game_state):
        pass

    def add_feedback(self, message):
        self.feedback.append(message)