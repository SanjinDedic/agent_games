import os
from pathlib import Path

from backend.database.db_models import League
from backend.games.greedy_pig.greedy_pig import GreedyPigGame

backend_dir = Path(__file__).parent

# Set up the test league
test_league_folder = os.path.join(
    backend_dir, "games", "greedy_pig", "leagues", "admin", "prelim7-8"
)
test_league = League(folder=test_league_folder, name="Test League", game="greedy_pig")


# Run a single game with feedback
print("Running a single game with feedback:")
game_result = GreedyPigGame.run_single_game_with_feedback(test_league)

# Print the feedback
print(game_result["feedback"])

# Print the final results
print("\nFinal Results:")
print(f"Points: {game_result['results']['points']}")
print(f"Score Aggregate: {game_result['results']['score_aggregate']}")

# Run multiple simulations
num_simulations = 100
print(f"\nRunning {num_simulations} simulations:")
simulation_results = GreedyPigGame.run_simulations(num_simulations, test_league)

print(f"\nResults after {num_simulations} simulations:")
print("Total Points:")
for player, points in simulation_results["total_points"].items():
    print(f"  {player}: {points}")

print("\nTotal Wins:")
for player, wins in simulation_results["total_wins"].items():
    print(f"  {player}: {wins}")
