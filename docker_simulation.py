import subprocess
import json

from jsonschema import validate, ValidationError

DOCKER_REPO = "matthewhee/agent_games:latest"

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

def run_docker_simulation(num_simulations, league_name, league_game, league_folder, custom_rewards):
    pull_command = ["docker", "pull", DOCKER_REPO]
    if subprocess.run(pull_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).returncode != 0:
        return False, "An error occurred while pulling the docker image"
    
    custom_rewards_str = ",".join(map(str, custom_rewards)) if custom_rewards else "None"
    command = ["docker", "run", DOCKER_REPO, str(num_simulations), league_name, league_game, league_folder, custom_rewards_str]
    docker_results = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if docker_results.returncode != 0:
        return False, "An error occurred while running the docker container"
    
    try:
        results = json.loads(docker_results.stdout)
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