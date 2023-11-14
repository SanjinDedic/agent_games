from player_base import Player

class Testing_Player(Player):
    def make_decision(self, game_state):
        if game_state['unbanked_money'][self.name] >= 15:
            return 'bank'
        return 'continue'
