from games.greedy_pig.player import Player

class CustomPlayer(Player):

    def make_decision(self, game_state):
        #You can random her if you wish to use it
        import random
        # Change this algorithm. You must return 'bank' or 'continue'.
        if game_state['unbanked_money'][self.name] >= 20:
            return 'bank'

        return 'continue'
