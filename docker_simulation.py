import subprocess
import json

from models_api import ErrorResponseModel

DOCKER_REPO = "matthewhee/agent_games:latest"

def run_docker_simulation(num_simulations, league_name, league_game, league_folder, custom_rewards):
    pull_command = ["docker", "pull", DOCKER_REPO]
    pull_result = subprocess.run(pull_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if pull_result.returncode != 0:
        return ErrorResponseModel(status="error", message="Failed to pull Docker image")
    
    custom_rewards_str = ",".join(map(str, custom_rewards)) if custom_rewards else "None"

    command = ["docker", "run", DOCKER_REPO, str(num_simulations), league_name, league_game, league_folder, custom_rewards_str]
    docker_results = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if docker_results.returncode != 0:
        return ErrorResponseModel(status="error", message="Failed to run Docker container", data=docker_results.stderr)
    
    json_string = docker_results.stdout.replace("'", '"')
    results = json.loads(json_string)
    return results