from player_base import Player

class New2_Player(Player):
    def make_decision(self, game_state):
        if self.my_rank(game_state) <= 3:
            return 'bank'
        return 'continue'