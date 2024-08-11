import subprocess
import json

from jsonschema import validate, ValidationError
from config import ROOT_DIR

DOCKER_REPO = "run-with-docker"
SUBPROCESS_TIMEOUT = 80  # 5 minutes timeout
DOCKER_TIMEOUT = 40

SIMULATION_RESULTS_SCHEMA = {
        "type": "object",
        "properties": {
            "total_points": {
                "type": "object",
                "patternProperties": {
                    ".*": {"type": "integer"}
                },
                "additionalProperties": False
            },
            "total_wins": {
                "type": "object",
                "patternProperties": {
                    ".*": {"type": "integer"}
                },
                "additionalProperties": False
            },
            "num_simulations": {"type": "integer"}
        },
        "required": ["total_points", "total_wins", "num_simulations"],
        "additionalProperties": False
    }

def run_docker_simulation(num_simulations, league_name, league_game, league_folder, custom_rewards, timeout=DOCKER_TIMEOUT):

    custom_rewards_str = ",".join(map(str, custom_rewards)) if custom_rewards else "None"
    command = ["docker", "run", "--rm","-v",f"{ROOT_DIR}:/agent_games", DOCKER_REPO, str(num_simulations), league_name, league_game, league_folder, custom_rewards_str, str(timeout)]
    try:
        docker_results = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=SUBPROCESS_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, "Timeout occurred while running the docker container"

    if docker_results.returncode != 0:
        return False, "An error occurred while running the docker container"
    print(docker_results.stdout)

    try:
        #read the results from results.json file in the current folder
        with open(ROOT_DIR+"/docker_results.json", "r") as f:
            results = json.load(f)

    except json.JSONDecodeError:
        return False, "An error occurred while parsing the simulation results"
    
    if not validate_docker_simulation_results(results):
        return False, "An error occurred while validating the simulation results"
    
    return True, results

def validate_docker_simulation_results(results):
    try:
        validate(instance=results, schema=SIMULATION_RESULTS_SCHEMA)
    except ValidationError:
        return False
    return True