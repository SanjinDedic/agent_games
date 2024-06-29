
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        leader_score = max(game_state["banked_money"].values())
        my_total = game_state["banked_money"][self.name] + game_state["unbanked_money"][self.name]

        if leader_score >= 70:
            if game_state["unbanked_money"][self.name] >= 15:
                return 'bank'
        elif leader_score >= 50:
            if game_state["unbanked_money"][self.name] >= 20:
                return 'bank'
        else:
            if game_state["unbanked_money"][self.name] >= 25:
                return 'bank'

        return 'continue'
