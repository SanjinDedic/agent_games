
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        my_total = game_state["banked_money"][self.name] + game_state["unbanked_money"][self.name]
        leader_total = max(game_state["banked_money"].values())

        if game_state["unbanked_money"][self.name] >= 20 or (my_total >= leader_total and game_state["unbanked_money"][self.name] > 0):
            return 'bank'
        return 'continue'
