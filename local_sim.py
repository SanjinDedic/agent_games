import os
import sys
from games.greedy_pig.greedy_pig import GreedyPigGame, run_simulations
from models_db import League

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

test_league_folder = os.path.join(current_dir, "games", "greedy_pig", "leagues", "test_league")

test_league = League(folder=test_league_folder, name="Test League", game="greedy_pig")

# Run 1000 simulations
num_simulations = 1000
results = run_simulations(num_simulations, test_league)
print(results)