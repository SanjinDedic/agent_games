from games.greedy_pig.player import Player

class CustomPlayer(Player):

  def make_decision(self, game_state):
    import random as rand

    # Change this algorithm. You must return 'bank' or 'continue'.
    my_ranking = self.my_rank(game_state)

    banked_top_5 = 15 + rand.randint(1, 2)
    banked_not_top = 24 + rand.randint(1, 2)
    
    if game_state['unbanked_money'][self.name] >= banked_not_top:
      return 'bank'

    return 'continue'
