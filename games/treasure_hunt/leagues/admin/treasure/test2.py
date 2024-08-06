from games.treasure_hunt.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 'left'
