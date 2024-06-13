import os
import sys
from games.greedy_pig.greedy_pig import Game
from games.greedy_pig.greedy_pig_sim import animate_simulations, run_simulations
from models_db import League



current_dir = os.path.dirname(os.path.abspath(__file__))
test_league_folder = os.path.join(current_dir, "games", "greedy_pig", "leagues", "test_league")

test_league2 = League(folder=test_league_folder, name="Test League")

game2 = Game(test_league2)
print("players in local sim game2",game2.players)

# Run 100 simulations
results = run_simulations(100, test_league2)

print("Results of 100 simulations:")
print(results)