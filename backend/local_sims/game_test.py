# game_test.py
import os
import sys

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame
from database.db_models import League
from datetime import datetime, timedelta

# Create a league instance
some_league = League(
    name="validation_leagueX",
    created_date=datetime.now(),
    expiry_date=datetime.now() + timedelta(days=1),
    game="prisoners_dilemma"
)

# Create the game
game = PrisonersDilemmaGame(league=some_league, verbose=True)

# Print initial state
print("\nValidation players type:", type(game.players))
print("Players content:", [(p.name, type(p)) for p in game.players])

# Define a custom player's code as a string
custom_player_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        print(f"DefectorMax making a move in round {game_state['round_number']}")
        return 'defect'
"""

# Add the custom player to the game
print("\nAttempting to add custom player...")
new_player = game.add_player(custom_player_code, "DefectorMax")

# Print state after adding player
print("\nPlayers after adding custom player:", [p.name for p in game.players])
print("Scores after adding player:", game.scores)

# Run simulations - NOW USING INSTANCE METHOD
print("\nRunning simulations...")
results = game.run_simulations(num_simulations=5, league=some_league, custom_rewards=None)
print("\nSimulation Results:", results)

# Print final state
print("\nFinal Players:", [p.name for p in game.players])
print("Final Scores:", game.scores)