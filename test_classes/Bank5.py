from player_base import Player

class CustomPlayer(Player):

    def make_decision(self, game_state):
        if game_state["unbanked_money"] > 5:
            return 'bank'
        return 'continue'