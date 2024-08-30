import os
import sys
from games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame
from models_db import League

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Set up the test league
test_league_folder = os.path.join(current_dir, "games", "prisoners_dilemma", "leagues", "test_league")
test_league = League(folder=test_league_folder, name="Test League", game="prisoners_dilemma")

# Run a single game with feedback
print("Running a single game with feedback:")
game_result = PrisonersDilemmaGame.run_single_game_with_feedback(test_league)

# Print the feedback
print(game_result['feedback'])

# Print the final results
print("\nFinal Results:")
print(f"Points: {game_result['results']['points']}")
print(f"Score Aggregate: {game_result['results']['score_aggregate']}")


'''
# Run multiple simulations
num_simulations = 100
print(f"\nRunning {num_simulations} simulations:")
simulation_results = PrisonersDilemmaGame.run_simulations(num_simulations, test_league)

print(f"\nResults after {num_simulations} simulations:")
print("Total Points:")
for player, points in simulation_results['total_points'].items():
    print(f"  {player}: {points}")

print("\nTotal Wins:")
for player, wins in simulation_results['total_wins'].items():
    print(f"  {player}: {wins}")
'''

# TO DO:
# 1. get rid of wins
# 2. Create some kind of filter so the that player who submitted the code only sees the results of their games ?
# 3. Find a way for admin to set the reward matrix for the game (maybe use the existing custom_rewards parameter)
# 4. Update instructions
# perhaps include these in the starter code:
#        my_opponent = game_state["opponent_name"]
#        opponent_history = game_state["opponent_history"]
#        my_history = game_state["my_history"]

# Add a print statement to show the game state in the default player code