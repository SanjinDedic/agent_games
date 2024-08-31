from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        my_opponent = game_state["opponent_name"]
        opponent_history = game_state["opponent_history"]
        my_history = game_state["my_history"]
        self.add_feedback(f"Round {game_state['round_number']}: Opponent history: {opponent_history}, My history: {my_history}")

        return 'defect'