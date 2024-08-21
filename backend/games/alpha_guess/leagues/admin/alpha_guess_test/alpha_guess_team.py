
from games.alpha_guess.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return random.choice('abcdefghijklmnopqrstuvwxyz')
