import asyncio
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
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


def run_single_simulation(game_class, league, custom_rewards=None):
    """Run a single simulation with the given parameters"""
    try:
        game = game_class(league)
        return game.play_game(custom_rewards)
    except Exception as e:
        logger.error(f"Error in simulation: {str(e)}")
        return None


async def run_parallel_simulations(
    game_class, league, num_sims=100, custom_rewards=None
):
    """Run multiple simulations in parallel using threads"""
    loop = asyncio.get_event_loop()
    futures = [
        loop.run_in_executor(
            executor, run_single_simulation, game_class, league, custom_rewards
        )
        for _ in range(num_sims)
    ]
    results = await asyncio.gather(*futures)
    return [r for r in results if r is not None]


@app.get("/")
async def health_check():
    return {"status": "healthy"}


@app.post("/simulate")
async def run_simulation(request: SimulationRequest):
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
        simulation_results = await run_parallel_simulations(
            game_class, league, request.num_simulations, request.custom_rewards
        )

        # Aggregate results - sum points without averaging
        total_points = {}
        table_data = {}

        # Initialize counters for each player
        for result in simulation_results:
            if result and "points" in result:
                for player in result["points"]:
                    if player not in total_points:
                        total_points[player] = 0

        # Sum up points
        for result in simulation_results:
            if result and "points" in result:
                for player, points in result["points"].items():
                    total_points[player] += points

        # Collect any additional table data from the last simulation
        if simulation_results and "table" in simulation_results[-1]:
            table_data = simulation_results[-1]["table"]

        return {
            "feedback": feedback_result["feedback"],
            "player_feedback": (
                feedback_result["player_feedback"]
                if request.player_feedback
                else "No player feedback"
            ),
            "simulation_results": {
                "total_points": total_points,
                "num_simulations": request.num_simulations,
                "table": table_data,
            },
        }

    except Exception as e:
        logger.error(f"Simulation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
