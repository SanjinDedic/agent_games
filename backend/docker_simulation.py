import json
import subprocess
import time

from config import ROOT_DIR
from jsonschema import ValidationError, validate

DOCKER_REPO = "run-with-docker"
SUBPROCESS_TIMEOUT = 80  # 5 minutes timeout
DOCKER_TIMEOUT = 40

SIMULATION_RESULTS_SCHEMA = {
    "type": "object",
    "properties": {
        "feedback": {
            "oneOf": [
                {"type": "string"},
                {"type": "object", "additionalProperties": True},
            ]
        },
        "player_feedback": {
            "oneOf": [
                {"type": "string"},
                {"type": "object", "additionalProperties": True},
            ]
        },
        "simulation_results": {
            "type": "object",
            "properties": {
                "total_points": {
                    "type": "object",
                    "patternProperties": {".*": {"type": "number"}},
                    "additionalProperties": False,
                },
                "num_simulations": {"type": "integer"},
                "table": {"type": "object", "additionalProperties": True},
            },
            "required": ["total_points", "num_simulations", "table"],
            "additionalProperties": False,
        },
    },
    "required": ["feedback", "simulation_results"],
    "additionalProperties": True,
}


def run_docker_simulation(
    league_name,
    league_game,
    league_folder,
    custom_rewards,
    timeout=DOCKER_TIMEOUT,
    player_feedback=False,
    num_simulations=100,
):
    custom_rewards_str = (
        ",".join(map(str, custom_rewards)) if custom_rewards else "None"
    )
    command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{ROOT_DIR}:/agent_games",
        DOCKER_REPO,
        league_name,
        league_game,
        league_folder,
        custom_rewards_str,
        str(timeout),
        str(player_feedback),
        str(num_simulations),
    ]

    print(f"Starting Docker simulation for {league_name}")
    start_time = time.time()

    try:
        subprocess_timeout = timeout - 0.5
        docker_results = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=subprocess_timeout,
        )
    except subprocess.TimeoutExpired:
        end_time = time.time()
        print(f"Docker simulation timed out after {end_time - start_time:.2f} seconds")
        return (
            False,
            "Timeout while running the docker container, your code might have an infinite loop",
        )

    end_time = time.time()
    print(f"Docker simulation completed in {end_time - start_time:.2f} seconds")

    if docker_results.returncode != 0:
        print(f"Docker simulation failed with return code {docker_results.returncode}")
        return (
            False,
            f"An error occurred while running the docker container: {docker_results.stderr}",
        )

    print(docker_results.stdout)

    try:
        # make the api call test here

        with open(ROOT_DIR + "/docker_results.json", "r") as f:
            results = json.load(f)

        print("Validating these Docker results")
        print(docker_results)
        validate(instance=results, schema=SIMULATION_RESULTS_SCHEMA)
        print("Docker results validation successful")

        return True, results

    except json.JSONDecodeError:
        print("Failed to parse Docker results JSON")
        return False, "An error occurred while parsing the simulation results"
    except FileNotFoundError:
        print("Docker results file not found")
        return False, "Docker results file not found"
    except ValidationError as ve:
        print(f"Docker results validation failed: {ve}")
        return False, f"Invalid results format: {ve}"


def validate_docker_results(results):
    try:
        validate(instance=results, schema=SIMULATION_RESULTS_SCHEMA)
        return True
    except ValidationError:
        return False
