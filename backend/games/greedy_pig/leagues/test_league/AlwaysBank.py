from games.greedy_pig.player import Player


class CustomPlayer(Player):

    def make_decision(self, game_state):
        return 'bank'
