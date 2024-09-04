import json
import sys
import os
import signal
import time
import logging

from games.game_factory import GameFactory
from models_db import League
from config import ROOT_DIR

# Set up logging to write to both a file and stream to stdout
log_file_path = os.path.join(ROOT_DIR, "dockerfile_script.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def timeout_handler(signum, frame):
    logger.error("Simulation timed out")
    raise TimeoutError("Simulation timed out")

def run_docker_simulations():
    logger.debug("Starting run_docker_simulations")
    print("Running docker simulation inside the container")
    if len(sys.argv) < 7:
        logger.error("Not enough arguments provided")
        return

    league_name, league_game, league_folder, timeout = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[5])
    custom_rewards = list(map(int, sys.argv[4].split(','))) if sys.argv[4] != "None" else None
    feedback_required = sys.argv[6].lower() == 'true'
    
    logger.debug(f"Arguments: {league_name}, {league_game}, {league_folder}, {timeout}, {custom_rewards}, {feedback_required}")
    
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
        feedback_result = "No feedback"
        if feedback_required:
            logger.debug("Running single game with feedback")
            feedback_result = game_class.run_single_game_with_feedback(league, custom_rewards)

        # Run multiple simulations
        logger.debug("Running multiple simulations")
        simulation_results = game_class.run_simulations(100, league, custom_rewards)

        signal.alarm(0)  # Cancel the alarm

        end_time = time.time()
        logger.debug(f"Simulation completed in {end_time - start_time:.2f} seconds")

        result = {
            "feedback": feedback_result['feedback'] if feedback_required else "No feedback",
            "simulation_results": simulation_results
        }

        logger.debug("Writing results to file")
        with open(ROOT_DIR + "/docker_results.json", "w") as f:
            json.dump(result, f)

    except TimeoutError:
        logger.error("Simulation timed out")
        result = {
            "feedback": "Simulation timed out. Your code might have an infinite loop.",
            "simulation_results": {"error": "Timeout"}
        }
        with open(ROOT_DIR + "/docker_results.json", "w") as f:
            json.dump(result, f)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        result = {
            "feedback": f"An error occurred: {str(e)}",
            "simulation_results": {"error": str(e)}
        }
        with open(ROOT_DIR + "/docker_results.json", "w") as f:
            json.dump(result, f)
    finally:
        # Ensure we always cancel the alarm
        signal.alarm(0)
        logger.debug("Docker simulation completed")

if __name__ == "__main__":
    run_docker_simulations()

# How to view the logs:
# 
# 1. File Logs:
#    The logs are being written to a file named 'dockerfile_script.log' in the ROOT_DIR.
#    You can view these logs by accessing this file after the script has run.
#    If you're running this in a Docker container, you can copy the log file out using:
#    docker cp <container_id>:/agent_games/dockerfile_script.log ./dockerfile_script.log
#    Then view it with: cat dockerfile_script.log
#    OR view the latest with: docker logs $(docker ps -q -l)
#
# 2. Console Output:
#    The logs are also being streamed to stdout, which means they will appear in the console output.
#    If you're running the Docker container interactively, you'll see these logs in real-time.
#    If you're running the container detached, you can view these logs using:
#    docker logs <container_id>
#
# 3. Docker Logging:
#    Docker captures anything written to stdout/stderr. To view logs of a running or stopped container:
#    docker logs <container_id>
#    For real-time logs: docker logs -f <container_id>
#
# 4. In Kubernetes:
#    If you're running this in a Kubernetes pod, you can view logs with:
#    kubectl logs <pod_name>
#    For real-time logs: kubectl logs -f <pod_name>
#
# Remember to replace <container_id> or <pod_name> with your actual container ID or pod name.