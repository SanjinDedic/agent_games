from games.forty_two.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return random.choice(['hit', 'stand'])