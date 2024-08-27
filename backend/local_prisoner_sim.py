import os
import sys
from games.prisoners_dilemma.prisoners_dilemma import run_simulations

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Define player classes directly in this file
class Player:
    def __init__(self, name):
        self.name = name

    def make_decision(self, opponent_history):
        pass

class AlwaysCooperatePlayer(Player):
    def make_decision(self, opponent_history):
        return 'collude'

class AlwaysDefectPlayer(Player):
    def make_decision(self, opponent_history):
        return 'defect'

class TitForTatPlayer(Player):
    def make_decision(self, opponent_history):
        opponent_last_move = opponent_history[-1] if opponent_history else None
        print("I am P3 Tit For Tat")
        print("Here is my oponents history")
        print(opponent_history)
        if not opponent_history:
            return 'collude'
        print("My opponents last move was", opponent_last_move, "so my response is", opponent_last_move)
        return opponent_history[-1]

# Create a list of players
players = [
    AlwaysCooperatePlayer("Player_1_AlwaysCooperate"),
    AlwaysDefectPlayer("Player_2_AlwaysDefect"),
    TitForTatPlayer("Player_3_TitForTat"),
    TitForTatPlayer("Player_4_TitForTat")
]

# Define the reward matrix
reward_matrix = {
    ('collude', 'collude'): (3, 3),
    ('collude', 'defect'): (0, 5),
    ('defect', 'collude'): (5, 0),
    ('defect', 'defect'): (1, 1)
}

# Run simulations
num_simulations = 1
total_scores = run_simulations(num_simulations, players, reward_matrix)

# Print the results
print(f"Results after {num_simulations} simulations:")
print(total_scores)

# Print the rankings
rankings = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)
print("\nRankings:")
for rank, (player, score) in enumerate(rankings, 1):
    print(f"{rank}. {player}: {score}")