from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        my_opponent = game_state["opponent_name"]
        opponent_history = game_state["opponent_history"]
        my_history = game_state["my_history"]
        
        # Your code here
        decision = 'collude'  # or 'defect'
        
        # Add custom feedback (will appear in blue in the game output)
        self.add_feedback(f"Round {game_state['round_number']}: Opponent history: {opponent_history}, My history: {my_history}, My decision: {decision}")
        
        return decision
