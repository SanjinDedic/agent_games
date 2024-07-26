import sys
import os

from games.game_factory import GameFactory
from models_db import League

def run_docker_simulations():
    num_simulations, league_name, league_game, league_folder = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
    custom_rewards = list(map(int, sys.argv[5].split(','))) if sys.argv[5] != "None" else None
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "games", league_game, league_folder)
    league = League(folder=folder, name=league_name, game=league_game)
    game_class = GameFactory.get_game_class(league.game)
    results = game_class.run_simulations(num_simulations, game_class, league, custom_rewards)
    print(results)

if __name__ == "__main__":
    run_docker_simulations()

