import os
import sys
from games.greedy_pig.greedy_pig import GreedyPigGame
from models_db import League

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

test_league_folder = os.path.join(current_dir, "games", "greedy_pig", "leagues", "test_league")

test_league = League(folder=test_league_folder, name="Test League", game="greedy_pig")

# Run a single game with feedback
game_result = GreedyPigGame.run_single_game_with_feedback(test_league)

# Print the feedback
print(game_result['feedback'])

# Print the final results
print("\nFinal Results:")
print(f"Total Points: {game_result['results']['points']}")
print(f"Score Aggregate: {game_result['results']['score_aggregate']}")