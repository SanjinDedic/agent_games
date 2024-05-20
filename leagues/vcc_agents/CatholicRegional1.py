from player import Player

class CustomPlayer(Player):

    def make_decision(self, game_state):
        #You can import random her if you wish to use it

        # Change this algorithm. You must return 'bank' or 'continue'.
      if game_state['unbanked_money'][self.name] >= 25:
            return 'bank'

      return 'continue'
