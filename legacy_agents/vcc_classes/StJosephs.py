from games.greedy_pig.player import Player

class CustomPlayer(Player):

    def make_decision(self, game_state):
      
      #You can random her if you wish to use it
        
        # Change this algorithm. You must return 'bank' or 'continue'.
        if len(game_state['players_banked_this_round'])>= 6:
            return 'bank'

        return 'continue'
