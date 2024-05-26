from games.greedy_pig.player import Player

class CustomPlayer(Player):

    def make_decision(self, game_state):
        import random
      #You can  random her if you wish to use it

        # Change this algorithm. You must return 'bank' or 'continue'.
        if game_state['unbanked_money'][self.name] > 22 or len(game_state['players_banked_this_round']) >= 9 or game_state['roll_no'] > 8:
            return 'bank'

        return 'continue'
