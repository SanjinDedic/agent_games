from games.prisoners_dilemma.player import Player


class CustomPlayer(Player):
    def make_decision(self, game_state):
        while True:
            print("u crash")
        # Your code here
        return 'collude'  # or 'defect'
