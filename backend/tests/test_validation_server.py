import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional

from config import ROOT_DIR
from fastapi import FastAPI, HTTPException
from games.game_factory import GameFactory
from models_db import League
from pydantic import BaseModel
from validation import is_agent_safe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=4)


class ValidationRequest(BaseModel):
    code: str
    game_name: str
    team_name: str
    num_simulations: int = 100
    custom_rewards: Optional[list] = None


def handle_simulation_error(e: Exception, context: str):
    """Standardized error handling"""
    error_msg = f"{context} error: {str(e)}"
    logger.error(error_msg)
    return {"status": "error", "message": error_msg}


def run_single_simulation(game_class, league, custom_rewards=None):
    try:
        game = game_class(league)
        return game.play_game(custom_rewards)
    except Exception as e:
        logger.error(f"Error in simulation: {str(e)}")
        return None


def run_parallel_simulations(game_class, league, num_sims=100, custom_rewards=None):
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(run_single_simulation, game_class, league, custom_rewards)
            for _ in range(num_sims)
        ]
        for future in futures:
            if future.result() is not None:
                results.append(future.result())
    return results


def aggregate_simulation_results(simulation_results, num_simulations):
    total_points = {}
    table_data = {}

    # Initialize counters for each player
    for result in simulation_results:
        if result and "points" in result:
            for player in result["points"]:
                if player not in total_points:
                    total_points[player] = 0

    # Sum points
    for result in simulation_results:
        if result and "points" in result:
            for player, points in result["points"].items():
                total_points[player] += points

    # Get table data from last successful simulation
    if simulation_results and "score_aggregate" in simulation_results[-1]:
        table_data = simulation_results[-1]["score_aggregate"]
    elif simulation_results and "table" in simulation_results[-1]:
        table_data = simulation_results[-1]["table"]

    return {
        "total_points": total_points,
        "num_simulations": num_simulations,
        "table": table_data,
    }


@app.post("/validate")
def validate_code(request: ValidationRequest):
    file_path = None
    try:
        if not is_agent_safe(request.code):
            return {"status": "error", "message": "Agent code is not safe"}

        if not request.code.strip():
            return {"status": "error", "message": "Code cannot be empty"}

        # Create test league
        test_league = League(
            name="test_league",
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=1),
            folder=f"leagues/test_league",
            game=request.game_name,
        )

        # Save the submitted code
        test_league_folder = os.path.join(
            ROOT_DIR, "games", request.game_name, "leagues/test_league"
        )
        os.makedirs(test_league_folder, exist_ok=True)

        file_path = os.path.join(test_league_folder, f"{request.team_name}.py")
        with open(file_path, "w") as f:
            f.write(request.code)

        # Get game class and run simulations
        game_class = GameFactory.get_game_class(request.game_name)

        # Run a single game with feedback first
        feedback_result = game_class.run_single_game_with_feedback(
            test_league, request.custom_rewards
        )

        # Run parallel simulations
        simulation_results = run_parallel_simulations(
            game_class, test_league, request.num_simulations, request.custom_rewards
        )

        # Aggregate results
        aggregated_results = aggregate_simulation_results(
            simulation_results, request.num_simulations
        )

        return {
            "status": "success",
            "feedback": feedback_result["feedback"],
            "player_feedback": feedback_result["player_feedback"],
            "simulation_results": aggregated_results,
        }

    except Exception as e:
        return handle_simulation_error(e, "Validation")
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
