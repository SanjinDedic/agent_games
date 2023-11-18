from player_base import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # You can her if you wish to use it
        import random

        # Change this algorithm. You must return 'bank' or 'continue'.
        if game_state["unbanked_money"][self.name] >= random.randint(24, 32):
            return "bank"

        return "continue"
