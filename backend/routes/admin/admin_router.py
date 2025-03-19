import json
import logging

import httpx
from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.config import DOCKER_API_URL
from backend.models_api import ErrorResponseModel, ResponseModel
from backend.routes.admin.admin_db import (
    create_agent_team,
    create_api_key,
    create_league,
    create_team,
    delete_all_demo_teams_and_subs,
    delete_team,
    get_all_demo_users,
    get_all_league_results,
    get_all_teams,
    get_league_by_id,
    publish_sim_results,
    save_simulation_results,
    update_expiry_date,
)
from backend.routes.admin.admin_models import (
    CreateAgentAPIKey,
    CreateAgentTeam,
    ExpiryDate,
    LeagueName,
    LeagueResults,
    LeagueSignUp,
    SimulationConfig,
    TeamDelete,
    TeamSignup,
)
from backend.routes.auth.auth_core import (
    get_current_user,
    verify_admin_role,
    verify_any_role,
)
from backend.routes.auth.auth_db import get_db
from backend.utils import transform_result

logger = logging.getLogger(__name__)

admin_router = APIRouter()


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

        data = create_league(session, league)
        return ResponseModel(
            status="success", message="League created successfully", data=data
        )
    except Exception as e:
        logger.error(f"Error creating league: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to create league: {str(e)}"
        )


@admin_router.post("/team-create", response_model=ResponseModel)
@verify_admin_role
async def create_team_endpoint(
    team: TeamSignup,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new team"""
    try:
        data = create_team(session, team)
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
        msg = delete_team(session, team.id)
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
    """Get all teams"""
    try:
        teams = get_all_teams(session)
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
        # Get the league using the ID
        league = get_league_by_id(session, simulation_config.league_id)
        if not league:
            return ErrorResponseModel(
                status="error",
                message=f"League with ID {simulation_config.league_id} not found",
            )
        # Make direct API call to simulation server
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{DOCKER_API_URL}/simulate",
                    json={
                        "league_id": simulation_config.league_id,
                        "game_name": league.game,
                        "num_simulations": simulation_config.num_simulations,
                        "custom_rewards": simulation_config.custom_rewards,
                        "player_feedback": True,
                    },
                    timeout=60.0,
                )

                if response.status_code != 200:
                    return ErrorResponseModel(
                        status="error",
                        message=f"Simulation failed with status code {response.status_code}: {response.text}",
                    )

                results = response.json()
                simulation_results = results.get("simulation_results")
                feedback = results.get("feedback")
                player_feedback = results.get("player_feedback")

                # Save simulation results if not a test league
                if league.name != "test_league":
                    try:
                        sim_result = save_simulation_results(
                            session,
                            league.id,
                            simulation_results,
                            simulation_config.custom_rewards,
                            feedback_str=(
                                feedback if isinstance(feedback, str) else None
                            ),
                            feedback_json=(
                                json.dumps(feedback)
                                if isinstance(feedback, dict)
                                else None
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

                response_data = transform_result(
                    simulation_results, sim_result, league.name
                )
                if feedback is not None:
                    response_data["feedback"] = feedback
                if player_feedback is not None:
                    response_data["player_feedback"] = player_feedback

                return ResponseModel(
                    status="success",
                    message="Simulation completed successfully",
                    data=response_data,
                )

            except httpx.HTTPError as e:
                logger.error(f"HTTP error occurred: {str(e)}")
                return ErrorResponseModel(
                    status="error",
                    message=f"Failed to connect to simulation service: {str(e)}",
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
        results = get_all_league_results(session, league.name)
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
        msg, data = publish_sim_results(
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
        msg = update_expiry_date(session, expiry.league, expiry.date)
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
            response = await client.get("http://localhost:8001/logs")
            if response.status_code == 200:
                return ResponseModel(
                    status="success",
                    message="Validator logs retrieved successfully",
                    data={"logs": response.json()["logs"]},
                )
            else:
                return ErrorResponseModel(
                    status="error",
                    message=f"Failed to retrieve validator logs: {response.text}",
                )
    except Exception as e:
        return ErrorResponseModel(
            status="error", message=f"Failed to connect to validator service: {str(e)}"
        )


@admin_router.get("/get-simulator-logs", response_model=ResponseModel)
@verify_admin_role
async def get_simulator_logs_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """Get logs from validator service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8002/logs")
            if response.status_code == 200:
                return ResponseModel(
                    status="success",
                    message="Simulator logs retrieved successfully",
                    data={"logs": response.json()["logs"]},
                )
            else:
                return ErrorResponseModel(
                    status="error",
                    message=f"Failed to retrieve simulator logs: {response.text}",
                )
    except Exception as e:
        return ErrorResponseModel(
            status="error", message=f"Failed to connect to simulator service: {str(e)}"
        )


@admin_router.post("/create-agent-team", response_model=ResponseModel)
@verify_admin_role
async def create_agent_team(
    request: CreateAgentTeam,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new agent team"""
    try:
        data = create_agent_team(session, request)
        return ResponseModel(
            status="success", message="Agent team created successfully", data=data
        )
    except Exception as e:
        logger.error(f"Error creating agent team: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to create agent team: {str(e)}"
        )


@admin_router.post("/create-agent-api-key", response_model=ResponseModel)
@verify_admin_role
async def create_agent_api_key(
    request: CreateAgentAPIKey,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new API key for an agent team"""
    try:
        data = create_api_key(session, request.team_id)
        return ResponseModel(
            status="success", message="API key created successfully", data=data
        )
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to create API key: {str(e)}"
        )


@admin_router.get("/get_all_demo_users", response_model=ResponseModel)
@verify_admin_role
async def get_all_demo_users_endpoint(
    session: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Get the name, number of sumbissions and time created for all demo users"""
    try:
        demo_users = get_all_demo_users(session)
        return ResponseModel(
            status="success", message="Demo users fetched successfully", data=demo_users
        )
    except Exception as e:
        return ErrorResponseModel(
            status="error", message=f"Failed to get the demo users{str(e)}"
        )


@admin_router.post("/delete_demo_teams_and_subs", response_model=ResponseModel)
@verify_admin_role
async def delete_all_demo_teams_and_submissions(
    session: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """
    Deletes all demo teams and submissions.
    
    This asynchronous endpoint attempts to remove all demo teams and their submissions, 
    and results they are involved in from the database using the provided session
    dependency. It returns a success response if the deletion completes successfully, 
    or an error response with details in case of failure.
    """
    try:
        delete_all_demo_teams_and_subs(session)
        return ResponseModel(
            status="success", message="All demo users deleted", data=None
        )
    except Exception as e:
        return ErrorResponseModel(
            status="error", message=f"Failed to delete demo users: {str(e)}"
        )
