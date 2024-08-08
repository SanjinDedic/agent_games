from games.alpha_guess.player import Player
import random
import string

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return random.choice(string.ascii_lowercase)