from player_base import Player

class CustomPlayer(Player):

    def make_decision(self, game_state):
        if game_state['unbanked_money'][self.name] >= 32:
            return 'bank'

        return 'continue'
