import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.database.db_models import League
from backend.games.game_factory import GameFactory

# Configure logging to use console only
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Only use StreamHandler for console output
)

logger = logging.getLogger(__name__)

app = FastAPI()


class SimulationRequest(BaseModel):
    league_id: int
    game_name: str
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


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/logs")
async def get_logs():
    """Return stub for logs since we're only using console logging"""
    return {"logs": "Logs are being streamed to console only. Check Docker logs."}


@app.post("/simulate")
async def run_simulation(request: SimulationRequest):
    """Run simulation with the provided parameters."""
    logger.info(f"Received simulation request: {request.model_dump()}")
    try:
        league = League(
            id=request.league_id,
            name="simulation_league",
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=1),
            game=request.game_name,
        )
        if not league:
            raise HTTPException(
                status_code=404, detail=f"League with ID {request.league_id} not found"
            )

        # Get game class and create single instance
        logger.info("Loading game class")
        game_class = GameFactory.get_game_class(request.game_name)
        game = game_class(league)
        logger.info(f"Game class loaded and instance created")

        # Load players
        await game.get_all_player_classes_via_api()
        logger.info(f"Players loaded: {game.players}")

        if not game.players:
            return {
                "status": "error",
                "message": "No players loaded for simulation",
                "simulation_results": {
                    "total_points": {},
                    "num_simulations": request.num_simulations,
                    "table": {},
                },
            }

        feedback_result = {
            "feedback": "No feedback",
            "player_feedback": "No player feedback",
        }

        # Run single game with feedback if requested
        if request.player_feedback:
            try:
                feedback_result = game.run_single_game_with_feedback(
                    request.custom_rewards
                )
            except Exception as e:
                logger.error(f"Error running feedback game: {str(e)}")
                return {
                    "status": "error",
                    "message": f"Error running feedback game: {str(e)}",
                    "simulation_results": {
                        "total_points": {},
                        "num_simulations": request.num_simulations,
                        "table": {},
                    },
                }

        # Run simulations sequentially
        simulation_results = []
        try:
            for _ in range(request.num_simulations):
                game.reset()
                result = game.play_game(request.custom_rewards)
                if result is not None:
                    simulation_results.append(result)

        except Exception as e:
            logger.error(f"Error running simulations: {str(e)}")
            return {
                "status": "error",
                "message": f"Error running simulations: {str(e)}",
                "simulation_results": {
                    "total_points": {},
                    "num_simulations": request.num_simulations,
                    "table": {},
                },
            }

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
        logger.error(f"Unexpected server error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Unexpected server error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
