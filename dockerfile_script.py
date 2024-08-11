import json
import sys
import os
import signal

from games.game_factory import GameFactory
from models_db import League
from config import ROOT_DIR

def timeout_handler(signum, frame):
    print("Simulation timed out")
    sys.exit(0)

def run_docker_simulations():
    if len(sys.argv) < 7:
        return
    
    num_simulations, league_name, league_game, league_folder, timeout = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[6])
    custom_rewards = list(map(int, sys.argv[5].split(','))) if sys.argv[5] != "None" else None
    folder = os.path.join(ROOT_DIR, "games", league_game, league_folder)
    league = League(folder=folder, name=league_name, game=league_game)
    game_class = GameFactory.get_game_class(league.game)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    results = game_class.run_simulations(num_simulations, game_class, league, custom_rewards)
    signal.alarm(0)
    
    with open(ROOT_DIR+"/docker_results.json", "w") as f:
        json.dump(results, f)
    

if __name__ == "__main__":
    run_docker_simulations()

