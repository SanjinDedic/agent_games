import json
import logging
import os
import signal
import sys
import time

from config import ROOT_DIR
from games.game_factory import GameFactory
from models_db import League

# Set up logging to write to both a file and stream to stdout
log_file_path = os.path.join(ROOT_DIR, "dockerfile_script.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file_path), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def timeout_handler(signum, frame):
    logger.error("Simulation timed out")
    raise TimeoutError("Simulation timed out")


def run_docker_simulations():
    logger.debug("Starting run_docker_simulations")
    print("Running docker simulation inside the container")
    if len(sys.argv) < 8:
        logger.error("Not enough arguments provided")
        return

    league_name, league_game, league_folder, timeout = (
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        int(sys.argv[5]),
    )
    custom_rewards = (
        list(map(int, sys.argv[4].split(","))) if sys.argv[4] != "None" else None
    )
    player_feedback = sys.argv[6].lower() == "true"
    num_simulations = int(sys.argv[7])

    args = {
        "league": league_name,
        "game": league_game,
        "folder": league_folder,
        "timeout": timeout,
        "rewards": custom_rewards,
        "feedback": player_feedback,
    }
    logger.debug(f"Arguments: {args}")

    folder = os.path.join(ROOT_DIR, "games", league_game, league_folder)
    logger.debug(f"Folder path: {folder}")

    league = League(folder=folder, name=league_name, game=league_game)
    game_class = GameFactory.get_game_class(league.game)
    logger.debug(f"Game class: {game_class}")

    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        start_time = time.time()

        # Run a single game with feedback if required
        feedback_result = {
            "feedback": "No feedback",
            "player_feedback": "No player feedback",
        }
        if player_feedback:
            logger.debug("Running single game with feedback")
            feedback_result = game_class.run_single_game_with_feedback(
                league, custom_rewards
            )

        # Run multiple simulations
        logger.debug(f"Running {num_simulations} simulations")
        simulation_results = game_class.run_simulations(
            num_simulations, league, custom_rewards
        )

        signal.alarm(0)  # Cancel the alarm

        end_time = time.time()
        logger.debug(f"Simulation completed in {end_time - start_time:.2f} seconds")

        result = {
            "feedback": feedback_result["feedback"],
            "player_feedback": (
                feedback_result["player_feedback"]
                if player_feedback
                else "No player feedback"
            ),
            "simulation_results": simulation_results,
        }

        logger.debug("Writing results to file")
        # testing API call here
        with open(ROOT_DIR + "/docker_results.json", "w") as f:
            json.dump(result, f)

    except TimeoutError:
        logger.error("Simulation timed out")
        result = {
            "feedback": "Simulation timed out. Your code might have an infinite loop.",
            "player_feedback": "No player feedback",
            "simulation_results": {"error": "Timeout"},
        }
        with open(ROOT_DIR + "/docker_results.json", "w") as f:
            json.dump(result, f)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        result = {
            "feedback": {"error": f"An error occurred: {str(e)}"},
            "player_feedback": {},  # Changed from string to empty object
            "simulation_results": {
                "total_points": {},
                "num_simulations": 0,
                "table": {},
            },
        }
        with open(ROOT_DIR + "/docker_results.json", "w") as f:
            json.dump(result, f)
    finally:
        # Ensure we always cancel the alarm
        signal.alarm(0)
        logger.debug("Docker simulation completed")


if __name__ == "__main__":
    run_docker_simulations()
