from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.config import GAMES
from backend.database.db_session import get_db
from backend.routes.agent.agent_db import allow_simulation, get_league_by_id
from backend.routes.agent.agent_models import SimulationRequest
from backend.routes.auth.auth_core import get_current_user, verify_ai_agent_role
from backend.tasks.celery_utils import poll_task_result
from backend.tasks.simulation_task import run_simulation as run_simulation_task

agent_router = APIRouter()

# Business failures surface via the HTTP status line, not a masked 200 envelope:
# SimulationLimitExceededError -> 429 (central handler in api.py); a missing league
# (404) and an unknown game (400) are request problems the router owns, raised here.
# Anything unexpected surfaces as a 500 rather than a swallowed error. The route
# returns the task's payload directly.


@agent_router.post("/simulate")
@verify_ai_agent_role
async def run_simulation(
    request: SimulationRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    league = get_league_by_id(session, request.league_id)
    if not league:
        raise HTTPException(
            status_code=404, detail=f"League with ID {request.league_id} not found"
        )
    if request.game_name not in GAMES:
        raise HTTPException(
            status_code=400, detail=f"Unknown game: {request.game_name}"
        )

    allow_simulation(current_user["team_id"])  # SimulationLimitExceededError -> 429

    async_result = run_simulation_task.delay(
        league_id=request.league_id,
        game_name=request.game_name,
        num_simulations=request.num_simulations,
        custom_rewards=request.custom_rewards,
        player_feedback=request.player_feedback,
    )
    return await poll_task_result(async_result, timeout=60)
