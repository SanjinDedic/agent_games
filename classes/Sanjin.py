from player_base import Player

class Testing_Player(Player):
    def make_decision(self, game_state):
        import random
        dice = random.randint(1, 6)
        if dice > 4:
            return "bank"
        else:
            return "continue"
