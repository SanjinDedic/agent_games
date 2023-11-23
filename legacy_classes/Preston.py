from player_base import Player

class CustomPlayer(Player):

    def make_decision(self, game_state):
        import random

        # Change this algorithm. You must return 'bank' or 'continue'.
        a=14+random.randint(-2,2)
        if game_state['unbanked_money'][self.name] >= a:
            return 'bank'

        return 'continue'
