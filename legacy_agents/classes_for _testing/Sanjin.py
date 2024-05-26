from games.greedy_pig.player import Player

class Testing_Player(Player):
    def make_decision(self, game_state):
        if len(game_state['players_banked_this_round']) > 2:
            return 'bank'
        return 'continue'
