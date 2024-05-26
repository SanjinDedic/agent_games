from games.greedy_pig.player import Player

class CustomPlayer(Player):

    def make_decision(self, game_state):
        import random
        #You can random here if you wish to use it
        threshhold = random.randint(20, 25)
        # Change this algorithm. You must return 'bank' or 'continue'.
        if game_state['unbanked_money'][self.name] >= threshhold and len(game_state['players_banked_this_round']) > 5:
            return 'bank'

        return 'continue'
