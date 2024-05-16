from player import Player

class CustomPlayer(Player):

    def make_decision(self, game_state):
      import random
      #You can  random her if you wish to use it
      
      my_ranking = self.my_rank(game_state)
      if my_ranking <= 4:
          if game_state['unbanked_money'][self.name] >= random.randint(12, 25) or len(game_state['players_banked_this_round']) > 4:
            return "bank"
          return "continue"
      else:
        if game_state['unbanked_money'][self.name] >= random.randint(15, 30) or len(game_state['players_banked_this_round']) > 4:
          return 'bank'
        return 'continue'
        
      # Change this algorithm. You must return 'bank' or 'continue'.
