from games.alpha_guess.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "b"