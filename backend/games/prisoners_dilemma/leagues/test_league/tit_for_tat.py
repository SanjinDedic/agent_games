from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        opponent_history = game_state['opponent_history']
        if not opponent_history:
            return 'collude'
        return opponent_history[-1]