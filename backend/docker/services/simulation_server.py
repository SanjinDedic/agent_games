import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from games.game_factory import GameFactory
from models_db import League
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=4)


class SimulationRequest(BaseModel):
    league_name: str
    league_game: str
    league_folder: str
    num_simulations: int = 100
    custom_rewards: Optional[List[int]] = None
    player_feedback: bool = False


class SimulationError(Exception):
    """Base exception for simulation errors"""

    pass


def handle_simulation_error(e: Exception, context: str):
    """Standardized error handling"""
    error_msg = f"{context} error: {str(e)}"
    logger.error(error_msg)
    raise HTTPException(status_code=500, detail=error_msg)


def run_single_simulation(game_class, league, custom_rewards=None):
    """Run a single simulation with the given parameters"""
    try:
        game = game_class(league)
        return game.play_game(custom_rewards)
    except Exception as e:
        logger.error(f"Error in simulation: {str(e)}")
        return None


def run_parallel_simulations(game_class, league, num_sims=100, custom_rewards=None):
    """Run multiple simulations in parallel using threads"""
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(run_single_simulation, game_class, league, custom_rewards)
            for _ in range(num_sims)
        ]
        for future in as_completed(futures):
            if future.result() is not None:
                results.append(future.result())
    return results


def aggregate_simulation_results(simulation_results, num_simulations):
    """Aggregate results from multiple simulations"""
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
    if simulation_results and "table" in simulation_results[-1]:
        table_data = simulation_results[-1]["table"]

    return {
        "total_points": total_points,
        "num_simulations": num_simulations,
        "table": table_data,
    }


@app.get("/")
def health_check():
    return {"status": "healthy"}


@app.post("/simulate")
def run_simulation(request: SimulationRequest):
    try:
        # Create league instance
        league = League(
            name=request.league_name,
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=1),
            folder=request.league_folder,
            game=request.league_game,
        )

        # Get game class
        game_class = GameFactory.get_game_class(request.league_game)

        # Run a single game with feedback if required
        feedback_result = {
            "feedback": "No feedback",
            "player_feedback": "No player feedback",
        }
        if request.player_feedback:
            feedback_result = game_class.run_single_game_with_feedback(
                league, request.custom_rewards
            )

        # Run parallel simulations
        simulation_results = run_parallel_simulations(
            game_class, league, request.num_simulations, request.custom_rewards
        )

        # Aggregate results
        aggregated_results = aggregate_simulation_results(
            simulation_results, request.num_simulations
        )

        return {
            "status": "success",
            "feedback": feedback_result["feedback"],
            "player_feedback": (
                feedback_result["player_feedback"]
                if request.player_feedback
                else "No player feedback"
            ),
            "simulation_results": aggregated_results,
        }

    except Exception as e:
        handle_simulation_error(e, "Simulation")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
