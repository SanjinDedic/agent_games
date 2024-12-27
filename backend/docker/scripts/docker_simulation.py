import json
import logging
import subprocess
import time

import httpx
from config import ROOT_DIR
from jsonschema import ValidationError, validate

logger = logging.getLogger(__name__)

DOCKER_REPO = "run-with-docker"
SUBPROCESS_TIMEOUT = 80  # 5 minutes timeout
DOCKER_TIMEOUT = 40
SIMULATION_URL = "http://localhost:8002/simulate"

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


class SimulationContainerError(Exception):
    pass


def is_container_running(container_name):
    """Check if a container is running"""
    try:
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={container_name}"],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


async def run_docker_simulation(
    league_name,
    league_game,
    league_folder,
    custom_rewards=None,
    timeout=DOCKER_TIMEOUT,
    player_feedback=False,
    num_simulations=100,
):
    try:
        if not is_container_running("simulator"):
            raise SimulationContainerError("Simulator container is not running")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    SIMULATION_URL,
                    json={
                        "league_name": league_name,
                        "league_game": league_game,
                        "league_folder": league_folder,
                        "custom_rewards": custom_rewards,
                        "player_feedback": player_feedback,
                        "num_simulations": num_simulations,
                    },
                    timeout=timeout,
                )

                if response.status_code != 200:
                    return (
                        False,
                        f"Simulation failed with status code {response.status_code}: {response.text}",
                    )

                results = response.json()
                return True, {
                    "feedback": results.get("feedback"),
                    "player_feedback": results.get("player_feedback"),
                    "simulation_results": results.get("simulation_results"),
                }

            except httpx.HTTPError as e:
                logger.error(f"HTTP error occurred: {str(e)}")
                return False, f"Failed to connect to simulation service: {str(e)}"
    except Exception as e:
        logger.error(f"Error running simulation: {str(e)}")
        return False, f"An error occurred while running the simulation: {str(e)}"


def validate_docker_results(results):
    try:
        validate(instance=results, schema=SIMULATION_RESULTS_SCHEMA)
        return True
    except ValidationError:
        return False
