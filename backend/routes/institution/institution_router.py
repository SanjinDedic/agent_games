import asyncio
import json
import logging
import os

from fastapi import APIRouter, Depends
from sqlmodel import Session
from backend.database.db_models import Institution
from backend.games.simulation_task import run_simulation
from backend.models_api import ErrorResponseModel, ResponseModel
from backend.routes.auth.auth_core import (
    get_current_user,
    verify_admin_or_institution,
    verify_institution_role,
)
from backend.database.db_session import get_db
from backend.routes.institution.institution_db import (
    assign_team_to_league,
    create_league,
    create_team,
    delete_league,
    delete_team,
    generate_signup_link,
    get_all_league_results,
    get_all_teams,
    get_league_by_id,
    get_unassigned_league,
    publish_sim_results,
    save_simulation_results,
    update_expiry_date,
    update_league_info,
    unassign_team,
)
from backend.routes.institution.institution_models import (
    ExpiryDate,
    LeagueDelete,
    LeagueIdRef,
    LeagueInfoUpdate,
    LeagueResults,
    LeagueSignUp,
    SimulationConfig,
    TeamDelete,
    TeamIdRef,
    TeamLeagueAssignment,
    TeamSignup,
)

logger = logging.getLogger(__name__)

institution_router = APIRouter()


class LeagueNotFoundError(Exception):
    """Raised when a league is not found"""

    pass


class InstitutionAccessError(Exception):
    """Raised when an institution tries to access data it doesn't own"""

    pass


def _resolve_institution(current_user: dict) -> tuple[int, bool]:
    """Extract institution_id and is_admin from the current user token."""
    institution_id = current_user.get("institution_id")
    is_admin = current_user["role"] == "admin"
    return institution_id, is_admin


@institution_router.post("/league-create", response_model=ResponseModel)
@verify_admin_or_institution
async def create_league_endpoint(
    league: LeagueSignUp,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new league for the institution"""
    try:
        institution_id, is_admin = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        data = create_league(session, league, institution_id)

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
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

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
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

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
        institution_id, is_admin = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        teams = get_all_teams(session, institution_id)
        return ResponseModel(
            status="success", message="Teams retrieved successfully", data=teams
        )
    except Exception as e:
        logger.error(f"Error retrieving teams: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve teams: {str(e)}"
        )


@institution_router.get("/subscription", response_model=ResponseModel)
@verify_institution_role
async def get_subscription_endpoint(
    session: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return the logged-in institution's subscription + contact details.

    Read-only view backing the Subscription tab. Stripe object IDs are not
    exposed — only display fields the institution needs to see.
    """
    try:
        institution_id, _ = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        institution = session.get(Institution, institution_id)
        if not institution:
            return ErrorResponseModel(
                status="error", message="Institution not found"
            )

        sub = institution.subscription
        data = {
            "institution_name": institution.name,
            "contact_person": institution.contact_person,
            "contact_email": institution.contact_email,
            "address": institution.address,
            "subscription": None,
        }
        if sub is not None:
            data["subscription"] = {
                "tier": sub.tier,
                "payment_method": sub.payment_method,
                "subscription_active": sub.subscription_active,
                "subscription_expiry": (
                    sub.subscription_expiry.isoformat()
                    if sub.subscription_expiry
                    else None
                ),
                "auto_renew": sub.auto_renew,
                "business_contact_name": sub.business_contact_name,
                "business_contact_email": sub.business_contact_email,
                "created_date": (
                    sub.created_date.isoformat() if sub.created_date else None
                ),
            }
        return ResponseModel(
            status="success", message="Subscription retrieved successfully", data=data
        )
    except Exception as e:
        logger.error(f"Error retrieving subscription: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve subscription: {str(e)}"
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
        institution_id, is_admin = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        # Get the league using the ID (admin bypasses ownership check)
        league = get_league_by_id(session, simulation_config.league_id, institution_id, is_admin=is_admin)

        # Check if institution has Docker access
        # For admin managing another institution's league, check the league's owning institution
        check_institution_id = league.institution_id if is_admin else institution_id
        institution = session.get(Institution, check_institution_id)
        if not institution.docker_access:
            return ErrorResponseModel(
                status="error",
                message="Your institution does not have Docker access. Please contact the administrator.",
            )

        # Enqueue the simulation task and wait for the result
        async_result = run_simulation.delay(
            league_id=simulation_config.league_id,
            game_name=league.game,
            num_simulations=simulation_config.num_simulations,
            custom_rewards=simulation_config.custom_rewards,
            player_feedback=True,
        )
        results = await asyncio.to_thread(async_result.get, timeout=300)
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
                feedback_str=(feedback if isinstance(feedback, str) else None),
                feedback_json=(
                    json.dumps(feedback) if isinstance(feedback, dict) else None
                ),
                is_admin=is_admin,
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

    except Exception as e:
        logger.error(f"Error running simulation: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to run simulation: {str(e)}"
        )


@institution_router.post("/get-all-league-results", response_model=ResponseModel)
@verify_admin_or_institution
async def get_league_results_endpoint(
    league: LeagueIdRef,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get all results for a specific league owned by the institution"""
    try:
        institution_id, is_admin = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        results = get_all_league_results(session, league.league_id, institution_id, is_admin=is_admin)
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
        institution_id, is_admin = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        msg, data = publish_sim_results(
            session, results.league_id, results.id, institution_id, results.feedback,
            is_admin=is_admin,
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
        institution_id, is_admin = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        msg = update_expiry_date(session, expiry.league_id, expiry.date, institution_id, is_admin=is_admin)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        logger.error(f"Error updating expiry date: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to update expiry date: {str(e)}"
        )


@institution_router.post("/update-league-info", response_model=ResponseModel)
@verify_admin_or_institution
async def update_league_info_endpoint(
    payload: LeagueInfoUpdate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Update the markdown info block shown to teams enrolled in this league."""
    try:
        institution_id, is_admin = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        msg = update_league_info(
            session,
            payload.league_id,
            payload.info_markdown,
            institution_id,
            is_admin=is_admin,
        )
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        logger.error(f"Error updating league info: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to update league info: {str(e)}"
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
        institution_id, is_admin = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        msg = assign_team_to_league(
            session, assignment.team_id, assignment.league_id, institution_id,
            is_admin=is_admin,
        )
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        logger.error(f"Error assigning team to league: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to assign team to league: {str(e)}"
        )


@institution_router.post("/generate-signup-link", response_model=ResponseModel)
@verify_admin_or_institution
async def generate_signup_link_endpoint(
    league: LeagueIdRef,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Generate a signup link for a league"""
    try:
        institution_id, is_admin = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        try:
            result = generate_signup_link(
                session, league.league_id, institution_id, is_admin=is_admin
            )
            return ResponseModel(
                status="success",
                message=f"Signup link generated for league {result['league_name']}",
                data={"signup_token": result["signup_token"]},
            )
        except LeagueNotFoundError:
            return ErrorResponseModel(
                status="error",
                message=f"League with ID {league.league_id} not found",
            )
        except InstitutionAccessError:
            return ErrorResponseModel(
                status="error",
                message="You don't have permission to access this league",
            )
    except Exception as e:
        logger.error(f"Error in signup link endpoint: {e}")
        return ErrorResponseModel(
            status="error",
            message=f"Server error while generating signup link: {str(e)}",
        )


@institution_router.post("/delete-league", response_model=ResponseModel)
@verify_admin_or_institution
async def delete_league_endpoint(
    league: LeagueDelete,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Delete a league and move all teams to the unassigned league"""
    try:
        institution_id, is_admin = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        msg = delete_league(session, league.league_id, institution_id, is_admin=is_admin)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        logger.error(f"Error deleting league: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to delete league: {str(e)}"
        )


@institution_router.post("/unassign-team", response_model=ResponseModel)
@verify_admin_or_institution
async def unassign_team_endpoint(
    team: TeamIdRef,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Move a team to the institution's 'unassigned' league without relying on client-provided league id."""
    try:
        institution_id, _ = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        msg = unassign_team(session, team.team_id, institution_id)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        logger.error(f"Error unassigning team: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to unassign team: {str(e)}"
        )
