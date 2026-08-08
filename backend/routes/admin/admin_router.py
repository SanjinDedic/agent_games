import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.database.db_models import UNASSIGNED_LEAGUE_NAME
from backend.database.db_session import get_db
from backend.errors import ProtectedLeagueError
from backend.routes.auth.auth_core import require_admin
from backend.routes.admin.admin_db import (
    assign_team_to_league,
    create_agent_team,
    create_api_key,
    create_league,
    create_team,
    delete_league,
    delete_team,
    generate_signup_link,
    generate_team_password_reset,
    get_all_league_results,
    get_all_teams,
    get_classroom_summaries,
    get_league_by_id,
    publish_sim_results,
    save_simulation_results,
    unassign_team,
    update_expiry_date,
    update_league_info,
)
from backend.routes.admin.admin_models import (
    CreateAgentAPIKey,
    CreateAgentTeam,
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
from backend.routes.user.user_db import get_latest_submissions_for_league
from backend.tasks.celery_utils import poll_task_result
from backend.tasks.simulation_task import run_simulation

logger = logging.getLogger(__name__)

admin_router = APIRouter(dependencies=[Depends(require_admin)])

# Every route here requires the admin role, enforced once by the router-level
# dependency above rather than per route — there is no endpoint in this module a
# team may call, so a missing per-route guard should be impossible rather than
# merely unlikely.
#
# Business failures raise domain exceptions mapped centrally in api.py:
# LeagueNotFoundError / TeamNotFoundError / SimulationResultNotFoundError -> 404,
# LeagueExistsError / TeamExistsError -> 409, SchoolsConfigError /
# ProtectedLeagueError -> 400. Anything unexpected surfaces as a 500 rather than
# a swallowed error. Data endpoints return their payload; action endpoints return
# {"message": ...}.


@admin_router.post("/league-create")
async def create_league_endpoint(
    league: LeagueSignUp,
    session: Session = Depends(get_db),
):
    """Create a new league."""
    return create_league(session, league)


@admin_router.post("/team-create")
async def team_create_endpoint(
    team: TeamSignup,
    session: Session = Depends(get_db),
):
    """Create a new team."""
    return create_team(session, team)


@admin_router.post("/delete-team")
async def delete_team_endpoint(
    team: TeamDelete,
    session: Session = Depends(get_db),
):
    """Delete a team."""
    return {"message": delete_team(session, team.id)}


@admin_router.get("/get-all-teams")
async def get_teams_endpoint(session: Session = Depends(get_db)):
    """Get every team in this deployment."""
    return get_all_teams(session)


@admin_router.get("/home")
async def get_home_endpoint(session: Session = Depends(get_db)):
    """Payload backing the admin home page: one card per league/classroom (team
    count, game, signup link)."""
    return {"classrooms": get_classroom_summaries(session)}


@admin_router.post("/run-simulation")
async def run_simulation_endpoint(
    simulation_config: SimulationConfig,
    session: Session = Depends(get_db),
):
    """Run a simulation for a league."""
    league = get_league_by_id(session, simulation_config.league_id)

    if league.name == UNASSIGNED_LEAGUE_NAME:
        raise ProtectedLeagueError(
            f"Cannot run simulations on the '{UNASSIGNED_LEAGUE_NAME}' league"
        )

    # Read the submitted code here (the API holds the DB session) and pass it to
    # the worker as a task arg, so the worker running untrusted agent code needs
    # no database credential.
    submissions = get_latest_submissions_for_league(
        session, simulation_config.league_id
    )

    async_result = run_simulation.delay(
        league_id=simulation_config.league_id,
        game_name=league.game,
        submissions=submissions,
        num_simulations=simulation_config.num_simulations,
        custom_rewards=simulation_config.custom_rewards,
        player_feedback=True,
    )
    results = await poll_task_result(async_result, timeout=300)

    # A failed run (e.g. no loadable players) must surface as an error, not be
    # stored: saving it would leave an empty result in the history that renders
    # as a rankings table with no rows and no explanation.
    if results.get("status") == "error":
        raise HTTPException(
            status_code=400,
            detail=results.get("message", "Simulation failed"),
        )

    simulation_results = results.get("simulation_results")
    feedback = results.get("feedback")
    player_feedback = results.get("player_feedback")

    sim_result = save_simulation_results(
        session,
        league.id,
        simulation_results,
        simulation_config.custom_rewards,
        feedback_str=(feedback if isinstance(feedback, str) else None),
        feedback_json=(json.dumps(feedback) if isinstance(feedback, dict) else None),
    )

    response_data = {
        "league_name": league.name,
        "id": sim_result.id if sim_result else None,
        "total_points": simulation_results["total_points"],
        "num_simulations": simulation_results["num_simulations"],
        # Present when the run hit the 10-minute cap: the count actually run
        # (num_simulations) is below what was requested.
        "requested_simulations": simulation_results.get(
            "requested_simulations", simulation_results["num_simulations"]
        ),
        "capped": simulation_results.get("capped", False),
        "timestamp": sim_result.timestamp if sim_result else None,
        "rewards": simulation_config.custom_rewards,
        "table": simulation_results.get("table", {}),
        "strategies": simulation_results.get("strategies", {}),
    }

    if feedback is not None:
        response_data["feedback"] = feedback
    if player_feedback is not None:
        response_data["player_feedback"] = player_feedback

    return response_data


@admin_router.post("/get-all-league-results")
async def get_league_results_endpoint(
    league: LeagueIdRef,
    session: Session = Depends(get_db),
):
    """Get all results for a specific league."""
    return get_all_league_results(session, league.league_id)


@admin_router.post("/publish-results")
async def publish_results_endpoint(
    results: LeagueResults,
    session: Session = Depends(get_db),
):
    """Publish simulation results for a league."""
    msg, data = publish_sim_results(
        session, results.league_id, results.id, results.feedback
    )
    return {"message": msg, **data}


@admin_router.post("/update-expiry-date")
async def update_expiry_endpoint(
    expiry: ExpiryDate,
    session: Session = Depends(get_db),
):
    """Update a league's expiry date."""
    return {"message": update_expiry_date(session, expiry.league_id, expiry.date)}


@admin_router.post("/update-league-info")
async def update_league_info_endpoint(
    payload: LeagueInfoUpdate,
    session: Session = Depends(get_db),
):
    """Update the markdown info block shown to teams enrolled in this league."""
    return {
        "message": update_league_info(
            session, payload.league_id, payload.info_markdown
        )
    }


@admin_router.post("/assign-team-to-league")
async def assign_team_endpoint(
    assignment: TeamLeagueAssignment,
    session: Session = Depends(get_db),
):
    """Assign a team to a league."""
    return {
        "message": assign_team_to_league(
            session, assignment.team_id, assignment.league_id
        )
    }


@admin_router.post("/generate-signup-link")
async def generate_signup_link_endpoint(
    league: LeagueIdRef,
    session: Session = Depends(get_db),
):
    """Generate a signup link for a league."""
    result = generate_signup_link(session, league.league_id)
    return {
        "message": f"Signup link generated for league {result['league_name']}",
        "signup_token": result["signup_token"],
    }


@admin_router.post("/team-password-reset")
async def team_password_reset_endpoint(
    team: TeamIdRef,
    session: Session = Depends(get_db),
):
    """Generate a shareable one-time password-reset link for a team."""
    result = generate_team_password_reset(session, team.team_id)
    return {
        "message": f"Password reset link generated for '{result['team_name']}'",
        "reset_token": result["reset_token"],
        "team_name": result["team_name"],
    }


@admin_router.post("/delete-league")
async def delete_league_endpoint(
    league: LeagueDelete,
    session: Session = Depends(get_db),
):
    """Delete a league and move all teams to the unassigned league."""
    return {"message": delete_league(session, league.league_id)}


@admin_router.post("/unassign-team")
async def unassign_team_endpoint(
    team: TeamIdRef,
    session: Session = Depends(get_db),
):
    """Move a team to the 'unassigned' league without relying on a
    client-provided league id."""
    return {"message": unassign_team(session, team.team_id)}


# --- agent teams (API-key driven, for the /agent router) --------------------


@admin_router.post("/create-agent-team")
async def create_agent_team_endpoint(
    request: CreateAgentTeam,
    session: Session = Depends(get_db),
):
    """Create a new agent team."""
    return create_agent_team(session, request)


@admin_router.post("/create-agent-api-key")
async def create_agent_api_key_endpoint(
    request: CreateAgentAPIKey,
    session: Session = Depends(get_db),
):
    """Create a new API key for an agent team."""
    return create_api_key(session, request.team_id)
