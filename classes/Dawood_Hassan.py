from player_base import Player

class Dawood_Hassan(Player):
    def make_decision(self, game_state):
        if game_state['unbanked_money'][self.name] >= 13:
            return 'bank'
        return 'continue'
