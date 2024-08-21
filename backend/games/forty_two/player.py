class Player:
    def __init__(self):
        self.name = None

    def make_decision(self, game_state):
        raise NotImplementedError("Subclasses must implement make_decision method")