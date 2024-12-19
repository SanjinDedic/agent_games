import asyncio
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from games.game_factory import GameFactory
from models_db import League
from pydantic import BaseModel

# Configure logging
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


@app.post("/validate")
async def validate_code(request: ValidationRequest):
    try:
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
            "/agent_games/games", request.game_name, "leagues/test_league"
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
        simulation_results = await run_parallel_simulations(
            game_class, test_league, request.num_simulations, request.custom_rewards
        )

        # Aggregate results
        total_points = {}
        for result in simulation_results:
            for player, points in result["points"].items():
                total_points[player] = total_points.get(player, 0) + points

        # Average the points
        for player in total_points:
            total_points[player] /= len(simulation_results)

        return {
            "status": "success",
            "feedback": feedback_result["feedback"],
            "player_feedback": feedback_result["player_feedback"],
            "simulation_results": {
                "total_points": total_points,
                "num_simulations": request.num_simulations,
            },
        }

    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the test file
        if os.path.exists(file_path):
            os.remove(file_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
