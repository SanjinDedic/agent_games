import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.config import get_service_url
from backend.models_api import ErrorResponseModel, ResponseModel
from backend.routes.agent.agent_db import (
    allow_simulation,
    get_league_by_id,
)
from backend.routes.agent.agent_models import SimulationRequest, ValidationRequest
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

        # Get environment-aware URL for simulator
        simulator_url = get_service_url("simulator", "simulate")
        logger.info(f"Using simulator URL: {simulator_url}")
        if not simulator_url:
            logger.error("Failed to get simulator URL from configuration")
            return ErrorResponseModel(
                status="error", message="Simulator service URL not configured"
            )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                simulator_url,
                json={
                    "league_id": request.league_id,
                    "game_name": request.game_name,
                    "num_simulations": request.num_simulations,
                    "custom_rewards": request.custom_rewards,
                    "player_feedback": request.player_feedback,
                },
                timeout=60.0,
            )

            if response.status_code != 200:
                return ErrorResponseModel(
                    status="error", message=f"Simulation failed: {response.text}"
                )

            simulation_result = response.json()
            return ResponseModel(
                status="success",
                message="Simulation completed successfully",
                data=simulation_result,
            )
    # Catch any exceptions and return an error response
    except Exception as e:
        logger.error(f"Error during simulation: {e}")
        return ErrorResponseModel(status="error", message=f"Simulation error: {str(e)}")
