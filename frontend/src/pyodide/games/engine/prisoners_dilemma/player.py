from abc import ABC, abstractmethod
import uuid

class Player(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.feedback = []

    @abstractmethod
    def make_decision(self, game_state):
        pass

    def add_feedback(self, message):
        self.feedback.append(message)