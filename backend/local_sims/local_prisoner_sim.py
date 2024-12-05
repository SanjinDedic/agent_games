import os
import sys

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.append(backend_dir)

from games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame
from models_db import League

# Set up the test league
test_league_folder = os.path.join(backend_dir, "games", "prisoners_dilemma", "leagues", "test_league")
test_league = League(folder=test_league_folder, name="Test League", game="prisoners_dilemma")

# Run a single game with feedback
print("Running a single game with feedback:")
game_result = PrisonersDilemmaGame.run_single_game_with_feedback(test_league)

# Print the feedbac
print("\nEntire Game Result")
print(game_result)

# Print the final results
print("\nFinal Results:")
print(f"Points: {game_result['results']['points']}")
print(f"Score Aggregate: {game_result['results']['score_aggregate']}")

# Run multiple simulations
num_simulations = 100
print(f"\nRunning {num_simulations} simulations:")
simulation_results = PrisonersDilemmaGame.run_simulations(num_simulations, test_league)

print(f"\nResults after {num_simulations} simulations:")
print("Total Points:")
for player, points in simulation_results['total_points'].items():
    print(f"  {player}: {points}")

print("\nDefections and Collusions:")
for player in simulation_results['table']['defections']:
    defections = simulation_results['table']['defections'][player]
    collusions = simulation_results['table']['collusions'][player]
    total_actions = defections + collusions
    defect_percentage = (defections / total_actions) * 100 if total_actions > 0 else 0
    collude_percentage = (collusions / total_actions) * 100 if total_actions > 0 else 0
    print(f"  {player}:")
    print(f"    Defections: {defections} ({defect_percentage:.2f}%)")
    print(f"    Collusions: {collusions} ({collude_percentage:.2f}%)")

# Run multiple simulations with custom rewards
num_simulations = 100
print(f"\nRunning {num_simulations} simulations to test 1,1,1,1 custom rewards (scores should be equal):")
simulation_results = PrisonersDilemmaGame.run_simulations(num_simulations, test_league, custom_rewards=[1, 1, 1, 1])

print(f"\nResults after {num_simulations} simulations with custom rewards:")
print("Total Points:")
for player, points in simulation_results['total_points'].items():
    print(f"  {player}: {points}")

print("\nDefections and Collusions:")
for player in simulation_results['table']['defections']:
    defections = simulation_results['table']['defections'][player]
    collusions = simulation_results['table']['collusions'][player]
    total_actions = defections + collusions
    defect_percentage = (defections / total_actions) * 100 if total_actions > 0 else 0
    collude_percentage = (collusions / total_actions) * 100 if total_actions > 0 else 0
    print(f"  {player}:")
    print(f"    Defections: {defections} ({defect_percentage:.2f}%)")
    print(f"    Collusions: {collusions} ({collude_percentage:.2f}%)")
