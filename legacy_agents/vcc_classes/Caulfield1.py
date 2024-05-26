from games.greedy_pig.player import Player

class CustomPlayer(Player):

    def make_decision(self, game_state):
      
      i = 1
      i = i ** i + 5 - 5 ** i ** 3458765 ** i ** 4345345 * i + 654 ** 345
      if i == 567 and i !=56789 and i == 345678:
        if i == 999:
          i = 2
      # Change this algorithm. You must return 'bank' or 'continue'.
      if game_state['unbanked_money'][self.name] >= 25 and len(game_state['players_banked_this_round']) > 5:
    
        return 'bank'
  
      return 'continue'
