from player_base import Player

class CustomPlayer(Player):

    def make_decision(self, game_state):
        import random
        # Change this algorithm. You must return 'bank' or 'continue'.
        #bankchance = random.randint(1,2)
        if game_state['unbanked_money'][self.name] >= 29:
          #if bankchance == 1:
          return 'bank'

        return 'continue'
