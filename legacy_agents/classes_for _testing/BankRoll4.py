from games.greedy_pig.player import Player

class CustomPlayer(Player):

    def make_decision(self, game_state):
        if game_state["roll_no"] == 4:
            return 'bank'
        return 'continue'