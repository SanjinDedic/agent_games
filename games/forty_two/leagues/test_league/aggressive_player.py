from games.forty_two.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["current_hand"] < 38:
            return 'hit'
        return 'stand'