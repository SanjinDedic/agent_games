import json
import logging
import httpx

from docker_utils.scripts.docker_simulation import run_docker_simulation
from fastapi import APIRouter, Depends, HTTPException
from games.game_factory import GameFactory
from models_api import ErrorResponseModel, ResponseModel
from routes.admin.admin_db import (
    create_league,
    create_team,
    delete_team,
    get_all_league_results,
    get_all_teams,
    get_league,
    publish_sim_results,
    save_simulation_results,
    update_expiry_date,
)
from routes.admin.admin_models import (
    ExpiryDate,
    LeagueName,
    LeagueResults,
    LeagueSignUp,
    SimulationConfig,
    TeamDelete,
    TeamSignup,
)
from routes.auth.auth_core import get_current_user, verify_admin_role, verify_any_role
from routes.auth.auth_db import get_db
from sqlmodel import Session
from utils import transform_result

logger = logging.getLogger(__name__)

admin_router = APIRouter()


# League Management Routes
@admin_router.post("/league-create", response_model=ResponseModel)
@verify_admin_role
async def create_league_endpoint(
    league: LeagueSignUp,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new league"""
    try:
        if not league.name:
            return ResponseModel(status="failed", message="League name cannot be empty")

        data = await create_league(session, league)
        return ResponseModel(
            status="success", message="League created successfully", data=data
        )
    except Exception as e:
        logger.error(f"Error creating league: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to create league: {str(e)}"
        )


# Team Management Routes
@admin_router.post("/team-create", response_model=ResponseModel)
@verify_admin_role
async def create_team_endpoint(
    team: TeamSignup,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new team"""
    try:
        data = await create_team(session, team)
        return ResponseModel(
            status="success", message="Team created successfully", data=data
        )
    except Exception as e:
        logger.error(f"Error creating team: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to create team: {str(e)}"
        )


@admin_router.post("/delete-team", response_model=ResponseModel)
@verify_admin_role
async def delete_team_endpoint(
    team: TeamDelete,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Delete a team"""
    try:
        msg = await delete_team(session, team.name)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        logger.error(f"Error deleting team: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to delete team: {str(e)}"
        )


@admin_router.get("/get-all-teams", response_model=ResponseModel)
@verify_admin_role
async def get_teams_endpoint(
    session: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    print("Get all teams called")
    """Get all teams"""
    try:
        teams = await get_all_teams(session)
        return ResponseModel(
            status="success", message="Teams retrieved successfully", data=teams
        )
    except Exception as e:
        logger.error(f"Error retrieving teams: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve teams: {str(e)}"
        )


@admin_router.post("/run-simulation", response_model=ResponseModel)
@verify_admin_role
async def run_simulation_endpoint(
    simulation_config: SimulationConfig,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Run a simulation"""
    try:
        try:
            league = await get_league(session, simulation_config.league_name)
        except Exception as e:
            logger.error(f"Error retrieving league: {str(e)}")
            return ErrorResponseModel(
                status="error",
                message=f"League '{simulation_config.league_name}' not found",
            )

        if simulation_config.use_docker:
            logger.info(f'Running simulation using Docker for league "{league.name}"')
            try:
                is_successful, results = await run_docker_simulation(
                    league.name,
                    league.game,
                    league.folder,
                    simulation_config.custom_rewards,
                    player_feedback=True,
                    num_simulations=simulation_config.num_simulations,
                )
            except Exception as e:
                logger.error(f"Error running docker simulation: {str(e)}")
                return ErrorResponseModel(
                    status="error",
                    message=f"An error occurred while running the simulation: {str(e)}",
                )
            if not is_successful:
                return ErrorResponseModel(status="error", message=results)

            simulation_results = results["simulation_results"]
            feedback = results.get("feedback")
            player_feedback = results.get("player_feedback")
        else:
            logger.info(f'Running simulation without Docker for league "{league.name}"')
            game_class = GameFactory.get_game_class(league.game)
            try:
                simulation_results = game_class.run_simulations(
                    simulation_config.num_simulations,
                    league,
                    simulation_config.custom_rewards,
                )
                feedback = None
                player_feedback = None
            except Exception as e:
                logger.error(f"Error running simulation: {str(e)}")
                return ErrorResponseModel(
                    status="error",
                    message=f"An error occurred while running the simulation: {str(e)}",
                )

        # Save simulation results regardless of Docker/non-Docker
        if league.name != "test_league":
            try:
                sim_result = await save_simulation_results(
                    session,
                    league.id,
                    simulation_results,
                    simulation_config.custom_rewards,
                    feedback_str=feedback if isinstance(feedback, str) else None,
                    feedback_json=(
                        json.dumps(feedback) if isinstance(feedback, dict) else None
                    ),
                )
            except Exception as e:
                logger.error(f"Error saving simulation results: {str(e)}")
                return ErrorResponseModel(
                    status="error",
                    message=f"An error occurred while saving the simulation results: {str(e)}",
                )
        else:
            sim_result = None

        response_data = transform_result(simulation_results, sim_result, league.name)
        if feedback is not None:
            response_data["feedback"] = feedback
        if player_feedback is not None:
            response_data["player_feedback"] = player_feedback

        return ResponseModel(
            status="success",
            message="Simulation completed successfully",
            data=response_data,
        )

    except Exception as e:
        logger.error(f"Error running simulation: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to run simulation: {str(e)}"
        )


@admin_router.post("/get-all-league-results", response_model=ResponseModel)
@verify_any_role
async def get_league_results_endpoint(
    league: LeagueName,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get all results for a specific league"""
    try:
        results = await get_all_league_results(session, league.name)
        return ResponseModel(
            status="success",
            message="League results retrieved successfully",
            data=results,
        )
    except Exception as e:
        logger.error(f"Error retrieving league results: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve league results: {str(e)}"
        )


@admin_router.post("/publish-results", response_model=ResponseModel)
@verify_admin_role
async def publish_results_endpoint(
    results: LeagueResults,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Publish simulation results"""
    try:
        msg, data = await publish_sim_results(
            session, results.league_name, results.id, results.feedback
        )
        return ResponseModel(status="success", message=msg, data=data)
    except Exception as e:
        logger.error(f"Error publishing results: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to publish results: {str(e)}"
        )


@admin_router.post("/update-expiry-date", response_model=ResponseModel)
@verify_admin_role
async def update_expiry_endpoint(
    expiry: ExpiryDate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Update league expiry date"""
    try:
        msg = await update_expiry_date(session, expiry.league, expiry.date)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        logger.error(f"Error updating expiry date: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to update expiry date: {str(e)}"
        )



@admin_router.get("/get-validator-logs", response_model=ResponseModel)  
@verify_admin_role
async def get_validator_logs_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """Get logs from validator service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get('http://localhost:8001/logs')
            if response.status_code == 200:
                return ResponseModel(
                    status="success",
                    message="Validator logs retrieved successfully",
                    data={"logs": response.json()["logs"]}
                )
            else:
                return ErrorResponseModel(
                    status="error",
                    message=f"Failed to retrieve validator logs: {response.text}"
                )
    except Exception as e:
        return ErrorResponseModel(
            status="error", 
            message=f"Failed to connect to validator service: {str(e)}"
        )

@admin_router.get("/get-simulator-logs", response_model=ResponseModel)  
@verify_admin_role
async def get_simulator_logs_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """Get logs from validator service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get('http://localhost:8002/logs')
            if response.status_code == 200:
                return ResponseModel(
                    status="success",
                    message="Simulator logs retrieved successfully",
                    data={"logs": response.json()["logs"]}
                )
            else:
                return ErrorResponseModel(
                    status="error",
                    message=f"Failed to retrieve simulator logs: {response.text}"
                )
    except Exception as e:
        return ErrorResponseModel(
            status="error", 
            message=f"Failed to connect to simulator service: {str(e)}"
        )