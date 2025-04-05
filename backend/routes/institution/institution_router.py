import json
import logging
import os

import httpx
from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.config import DOCKER_API_URL
from backend.database.db_models import Institution
from backend.models_api import ErrorResponseModel, ResponseModel
from backend.routes.auth.auth_core import (
    get_current_user,
    verify_admin_or_institution,
    verify_institution_role,
)
from backend.routes.auth.auth_db import get_db
from backend.routes.institution.institution_db import (assign_team_to_league,
                                                       create_league,
                                                       create_team,
                                                       delete_team,
                                                       get_all_league_results,
                                                       get_all_teams,
                                                       get_league_by_id,
                                                       publish_sim_results,
                                                       save_simulation_results,
                                                       update_expiry_date)
from backend.routes.institution.institution_models import (
    ExpiryDate, LeagueName, LeagueResults, LeagueSignUp, SimulationConfig,
    TeamDelete, TeamLeagueAssignment, TeamSignup)

logger = logging.getLogger(__name__)

institution_router = APIRouter()


@institution_router.post("/league-create", response_model=ResponseModel)
@verify_admin_or_institution
async def create_league_endpoint(
    league: LeagueSignUp,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new league for the institution"""
    try:
        institution_id = current_user.get("institution_id")
        if not institution_id:
            return ErrorResponseModel(status="error", message="Institution ID not found in token")

        data = create_league(session, league.model_dump(), institution_id)

        return ResponseModel(
            status="success", message="League created successfully", data=data
        )
    except Exception as e:
        logger.error(f"Error creating league: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to create league: {str(e)}"
        )


@institution_router.post("/team-create", response_model=ResponseModel)
@verify_institution_role
async def team_create_endpoint(
    team: TeamSignup,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new team for the institution"""
    try:
        institution_id = current_user.get("institution_id")
        if not institution_id:
            return ErrorResponseModel(status="error", message="Institution ID not found in token")

        data = create_team(session, team, institution_id)
        return ResponseModel(
            status="success", message="Team created successfully", data=data
        )
    except Exception as e:
        logger.error(f"Error creating team: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to create team: {str(e)}"
        )


@institution_router.post("/delete-team", response_model=ResponseModel)
@verify_institution_role
async def delete_team_endpoint(
    team: TeamDelete,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Delete a team"""
    try:
        institution_id = current_user.get("institution_id")
        if not institution_id:
            return ErrorResponseModel(status="error", message="Institution ID not found in token")

        msg = delete_team(session, team.id, institution_id)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        logger.error(f"Error deleting team: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to delete team: {str(e)}"
        )


@institution_router.get("/get-all-teams", response_model=ResponseModel)
@verify_admin_or_institution
async def get_teams_endpoint(
    session: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get all teams for the institution"""
    try:
        if current_user["role"] == "admin":
            institution_id = 1
        else:
            institution_id = current_user.get("institution_id")
        if not institution_id:
            return ErrorResponseModel(status="error", message="Institution ID not found in token")

        teams = get_all_teams(session, institution_id)
        return ResponseModel(
            status="success", message="Teams retrieved successfully", data=teams
        )
    except Exception as e:
        logger.error(f"Error retrieving teams: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve teams: {str(e)}"
        )


@institution_router.post("/run-simulation", response_model=ResponseModel)
@verify_admin_or_institution
async def run_simulation_endpoint(
    simulation_config: SimulationConfig,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Run a simulation for a league owned by the institution"""
    try:
        if current_user["role"] == "admin":
            institution_id = 1
        else:
            institution_id = current_user.get("institution_id")
        if not institution_id:
            return ErrorResponseModel(status="error", message="Institution ID not found in token")

        # Get the league using the ID
        league = get_league_by_id(session, simulation_config.league_id, institution_id)

        # Check if institution has Docker access
        institution = session.get(Institution, institution_id)
        if not institution.docker_access:
            return ErrorResponseModel(
                status="error", 
                message="Your institution does not have Docker access. Please contact the administrator."
            )

        # Make direct API call to simulation server
        try:
            async with httpx.AsyncClient() as client:
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

                # Save simulation results
                try:
                    sim_result = save_simulation_results(
                        session,
                        league.id,
                        institution_id,
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

                response_data = {
                    "league_name": league.name,
                    "id": sim_result.id if sim_result else None,
                    "total_points": simulation_results["total_points"],
                    "num_simulations": simulation_results["num_simulations"],
                    "timestamp": sim_result.timestamp if sim_result else None,
                    "rewards": simulation_config.custom_rewards,
                    "table": simulation_results.get("table", {}),
                }

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


@institution_router.post("/get-all-league-results", response_model=ResponseModel)
@verify_admin_or_institution
async def get_league_results_endpoint(
    league: LeagueName,  # Change from LeagueSignUp to LeagueName
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get all results for a specific league owned by the institution"""
    try:
        if current_user["role"] == "admin":
            institution_id = 1
        else:
            institution_id = current_user.get("institution_id")
        if not institution_id:
            return ErrorResponseModel(status="error", message="Institution ID not found in token")

        results = get_all_league_results(session, league.name, institution_id)
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


@institution_router.post("/publish-results", response_model=ResponseModel)
@verify_admin_or_institution
async def publish_results_endpoint(
    results: LeagueResults,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Publish simulation results for a league owned by the institution"""
    try:
        institution_id = current_user.get("institution_id")
        if not institution_id:
            return ErrorResponseModel(status="error", message="Institution ID not found in token")

        msg, data = publish_sim_results(
            session, results.league_name, results.id, institution_id, results.feedback
        )
        return ResponseModel(status="success", message=msg, data=data)
    except Exception as e:
        logger.error(f"Error publishing results: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to publish results: {str(e)}"
        )


@institution_router.post("/update-expiry-date", response_model=ResponseModel)
@verify_admin_or_institution
async def update_expiry_endpoint(
    expiry: ExpiryDate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Update league expiry date for a league owned by the institution"""
    try:
        institution_id = current_user.get("institution_id")
        if not institution_id:
            return ErrorResponseModel(status="error", message="Institution ID not found in token")

        msg = update_expiry_date(session, expiry.league, expiry.date, institution_id)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        logger.error(f"Error updating expiry date: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to update expiry date: {str(e)}"
        )


@institution_router.post("/assign-team-to-league", response_model=ResponseModel)
@verify_admin_or_institution
async def assign_team_endpoint(
    assignment: TeamLeagueAssignment,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Assign a team to a league within the institution"""
    try:
        institution_id = current_user.get("institution_id")
        if not institution_id:
            return ErrorResponseModel(status="error", message="Institution ID not found in token")

        msg = assign_team_to_league(session, assignment.team_id, assignment.league_id, institution_id)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        logger.error(f"Error assigning team to league: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to assign team to league: {str(e)}"
        )
