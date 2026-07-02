import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.celery_utils import poll_task_result
from backend.games.simulation_task import run_simulation as run_simulation_task
from backend.models_api import ErrorResponseModel, ResponseModel
from backend.routes.agent.agent_db import (
    allow_simulation,
    get_league_by_id,
)
from backend.routes.agent.agent_models import SimulationRequest
from backend.routes.auth.auth_core import get_current_user, verify_ai_agent_role
from backend.database.db_session import get_db

logger = logging.getLogger(__name__)

agent_router = APIRouter()


@agent_router.post("/simulate", response_model=ResponseModel)
@verify_ai_agent_role
async def run_simulation(
    request: SimulationRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    try:
        league = get_league_by_id(session, request.league_id)
        if not league:
            return ErrorResponseModel(
                status="error", message=f"League with ID {request.league_id} not found"
            )
        team_id = current_user["team_id"]
        allow_simulate = allow_simulation(session, team_id)
        if not allow_simulate:
            return ErrorResponseModel(
                status="error",
                message="Simulation is rate limited.",
            )

        async_result = run_simulation_task.delay(
            league_id=request.league_id,
            game_name=request.game_name,
            num_simulations=request.num_simulations,
            custom_rewards=request.custom_rewards,
            player_feedback=request.player_feedback,
        )
        simulation_result = await poll_task_result(async_result, timeout=60)
        return ResponseModel(
            status="success",
            message="Simulation completed successfully",
            data=simulation_result,
        )
    # Catch any exceptions and return an error response
    except Exception as e:
        logger.error(f"Error during simulation: {e}")
        return ErrorResponseModel(status="error", message=f"Simulation error: {str(e)}")
