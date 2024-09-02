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
    print("Running docker simulation inside the container")
    if len(sys.argv) < 7:
        return

    league_name, league_game, league_folder, timeout = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[5])
    custom_rewards = list(map(int, sys.argv[4].split(','))) if sys.argv[4] != "None" else None
    feedback_required = sys.argv[6].lower() == 'true'
    
    folder = os.path.join(ROOT_DIR, "games", league_game, league_folder)
    league = League(folder=folder, name=league_name, game=league_game)
    game_class = GameFactory.get_game_class(league.game)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)

    # Run a single game with feedback if required
    feedback_result = "No feedback"
    if feedback_required:
        feedback_result = game_class.run_single_game_with_feedback(league, custom_rewards)

    # Run multiple simulations
    simulation_results = game_class.run_simulations(100, league, custom_rewards)

    signal.alarm(0)

    result = {
        "feedback": feedback_result['feedback'] if feedback_required else "No feedback",
        "simulation_results": simulation_results
    }

    with open(ROOT_DIR + "/docker_results.json", "w") as f:
        json.dump(result, f)

if __name__ == "__main__":
    run_docker_simulations()