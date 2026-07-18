import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.database.db_models import Institution
from backend.database.db_session import get_db
from backend.routes.auth.auth_core import (
    get_current_user,
    verify_admin_or_institution,
    verify_institution_role,
)
from backend.routes.institution.institution_db import (
    ProtectedLeagueError,
    assign_team_to_league,
    create_league,
    create_team,
    delete_league,
    delete_team,
    generate_signup_link,
    get_all_league_results,
    get_all_teams,
    get_league_by_id,
    get_teams_progress,
    get_tutorials_progress,
    publish_sim_results,
    save_simulation_results,
    unassign_team,
    update_expiry_date,
    update_league_info,
)
from backend.routes.institution.institution_models import (
    ExpiryDate,
    LeagueDelete,
    LeagueIdRef,
    LeagueInfoUpdate,
    LeagueResults,
    LeagueSignUp,
    LeagueTutorialsUpdate,
    SimulationConfig,
    TeamDelete,
    TeamIdRef,
    TeamLeagueAssignment,
    TeamSignup,
)
from backend.routes.tutorial.tutorial_db import (
    get_league_tutorial_ids,
    set_league_tutorials,
)
from backend.routes.user.user_db import get_latest_submissions_for_league
from backend.tasks.celery_utils import poll_task_result
from backend.tasks.simulation_task import run_simulation

logger = logging.getLogger(__name__)

institution_router = APIRouter()

# Business failures surface via the HTTP status line, not a masked 200 envelope.
# League/team lookups and ownership checks raise domain exceptions mapped centrally
# in api.py: LeagueNotFoundError / TeamNotFoundError / SimulationResultNotFoundError
# -> 404, InstitutionAccessError -> 403, LeagueExistsError / TeamExistsError -> 409,
# SchoolsConfigError / ProtectedLeagueError -> 400. A token missing its institution_id
# and a missing Docker grant are request problems the router owns, raised inline.
# Anything unexpected surfaces as a 500 rather than a swallowed error. Each route
# returns its payload directly: data endpoints return the payload, action endpoints
# return {"message": ...}.


def _resolve_institution(current_user: dict) -> tuple[int, bool]:
    """Extract (institution_id, is_admin) from the current user token.

    Pure lookup with no validation — also imported by the user and ai routers,
    which apply their own missing-id handling. Institution endpoints here use
    ``_require_institution`` to reject a token that carries no institution id.
    """
    institution_id = current_user.get("institution_id")
    is_admin = current_user["role"] == "admin"
    return institution_id, is_admin


def _require_institution(current_user: dict) -> tuple[int, bool]:
    """Resolve the institution context, rejecting a token that lacks it.

    Both admin (institution_id=1) and institution tokens carry an id, so a
    missing id is a malformed-request problem this router owns -> HTTP 400.
    """
    institution_id, is_admin = _resolve_institution(current_user)
    if not institution_id:
        raise HTTPException(
            status_code=400, detail="Institution ID not found in token"
        )
    return institution_id, is_admin


@institution_router.post("/league-create")
@verify_admin_or_institution
async def create_league_endpoint(
    league: LeagueSignUp,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new league for the institution."""
    institution_id, _ = _require_institution(current_user)
    return create_league(session, league, institution_id)


@institution_router.post("/team-create")
@verify_institution_role
async def team_create_endpoint(
    team: TeamSignup,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new team for the institution."""
    institution_id, _ = _require_institution(current_user)
    return create_team(session, team, institution_id)


@institution_router.post("/delete-team")
@verify_institution_role
async def delete_team_endpoint(
    team: TeamDelete,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Delete a team."""
    institution_id, _ = _require_institution(current_user)
    return {"message": delete_team(session, team.id, institution_id)}


@institution_router.get("/get-all-teams")
@verify_admin_or_institution
async def get_teams_endpoint(
    session: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get all teams for the institution."""
    institution_id, _ = _require_institution(current_user)
    return get_all_teams(session, institution_id)


@institution_router.get("/team-progress")
@verify_admin_or_institution
async def team_progress_endpoint(
    session: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Data backing the Team Progress tab: per-team agent submission stats
    plus per-exercise completion counts for each tutorial attached to the
    institution's leagues."""
    institution_id, _ = _require_institution(current_user)
    return {
        "teams": get_teams_progress(session, institution_id),
        "tutorials": get_tutorials_progress(session, institution_id),
    }


@institution_router.get("/subscription")
@verify_institution_role
async def get_subscription_endpoint(
    session: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return the logged-in institution's subscription + contact details.

    Read-only view backing the Subscription tab. Stripe object IDs are not
    exposed — only display fields the institution needs to see.
    """
    institution_id, _ = _require_institution(current_user)

    institution = session.get(Institution, institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    sub = institution.subscription
    data = {
        "institution_name": institution.name,
        "contact_person": institution.contact_person,
        "contact_email": institution.contact_email,
        "address": institution.address,
        "is_teacher": institution.is_teacher,
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
    return data


@institution_router.post("/run-simulation")
@verify_admin_or_institution
async def run_simulation_endpoint(
    simulation_config: SimulationConfig,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Run a simulation for a league owned by the institution."""
    institution_id, is_admin = _require_institution(current_user)

    # Get the league using the ID (admin bypasses ownership check)
    league = get_league_by_id(
        session, simulation_config.league_id, institution_id, is_admin=is_admin
    )

    if league.name == "unassigned":
        raise ProtectedLeagueError(
            "Cannot run simulations on the 'unassigned' league"
        )

    # Read the submitted code here (the API holds the DB session) and pass it to
    # the worker as a task arg, so the worker running untrusted agent code needs
    # no database credential.
    submissions = get_latest_submissions_for_league(
        session, simulation_config.league_id
    )

    # Enqueue the simulation task and wait for the result
    async_result = run_simulation.delay(
        league_id=simulation_config.league_id,
        game_name=league.game,
        submissions=submissions,
        num_simulations=simulation_config.num_simulations,
        custom_rewards=simulation_config.custom_rewards,
        player_feedback=True,
    )
    results = await poll_task_result(async_result, timeout=300)
    simulation_results = results.get("simulation_results")
    feedback = results.get("feedback")
    player_feedback = results.get("player_feedback")

    sim_result = save_simulation_results(
        session,
        league.id,
        institution_id,
        simulation_results,
        simulation_config.custom_rewards,
        feedback_str=(feedback if isinstance(feedback, str) else None),
        feedback_json=(json.dumps(feedback) if isinstance(feedback, dict) else None),
        is_admin=is_admin,
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


@institution_router.post("/get-all-league-results")
@verify_admin_or_institution
async def get_league_results_endpoint(
    league: LeagueIdRef,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get all results for a specific league owned by the institution."""
    institution_id, is_admin = _require_institution(current_user)
    return get_all_league_results(
        session, league.league_id, institution_id, is_admin=is_admin
    )


@institution_router.post("/publish-results")
@verify_admin_or_institution
async def publish_results_endpoint(
    results: LeagueResults,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Publish simulation results for a league owned by the institution."""
    institution_id, is_admin = _require_institution(current_user)
    msg, data = publish_sim_results(
        session,
        results.league_id,
        results.id,
        institution_id,
        results.feedback,
        is_admin=is_admin,
    )
    return {"message": msg, **data}


@institution_router.post("/update-expiry-date")
@verify_admin_or_institution
async def update_expiry_endpoint(
    expiry: ExpiryDate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Update league expiry date for a league owned by the institution."""
    institution_id, is_admin = _require_institution(current_user)
    return {
        "message": update_expiry_date(
            session, expiry.league_id, expiry.date, institution_id, is_admin=is_admin
        )
    }


@institution_router.post("/update-league-info")
@verify_admin_or_institution
async def update_league_info_endpoint(
    payload: LeagueInfoUpdate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Update the markdown info block shown to teams enrolled in this league."""
    institution_id, is_admin = _require_institution(current_user)
    return {
        "message": update_league_info(
            session,
            payload.league_id,
            payload.info_markdown,
            institution_id,
            is_admin=is_admin,
        )
    }


@institution_router.post("/get-league-tutorials")
@verify_admin_or_institution
async def get_league_tutorials_endpoint(
    payload: LeagueIdRef,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Ids of the tutorials attached to one of the caller's leagues."""
    institution_id, is_admin = _require_institution(current_user)
    league = get_league_by_id(
        session, payload.league_id, institution_id, is_admin=is_admin
    )
    return {"tutorial_ids": get_league_tutorial_ids(session, league.id)}


@institution_router.post("/update-league-tutorials")
@verify_admin_or_institution
async def update_league_tutorials_endpoint(
    payload: LeagueTutorialsUpdate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Replace the set of tutorials attached to one of the caller's leagues."""
    institution_id, is_admin = _require_institution(current_user)
    league = get_league_by_id(
        session, payload.league_id, institution_id, is_admin=is_admin
    )
    tutorial_ids = set_league_tutorials(session, league.id, payload.tutorial_ids)
    return {
        "message": f"Tutorials updated for league '{league.name}'",
        "tutorial_ids": tutorial_ids,
    }


@institution_router.post("/assign-team-to-league")
@verify_admin_or_institution
async def assign_team_endpoint(
    assignment: TeamLeagueAssignment,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Assign a team to a league within the institution."""
    institution_id, is_admin = _require_institution(current_user)
    return {
        "message": assign_team_to_league(
            session,
            assignment.team_id,
            assignment.league_id,
            institution_id,
            is_admin=is_admin,
        )
    }


@institution_router.post("/generate-signup-link")
@verify_admin_or_institution
async def generate_signup_link_endpoint(
    league: LeagueIdRef,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Generate a signup link for a league."""
    institution_id, is_admin = _require_institution(current_user)
    result = generate_signup_link(
        session, league.league_id, institution_id, is_admin=is_admin
    )
    return {
        "message": f"Signup link generated for league {result['league_name']}",
        "signup_token": result["signup_token"],
    }


@institution_router.post("/delete-league")
@verify_admin_or_institution
async def delete_league_endpoint(
    league: LeagueDelete,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Delete a league and move all teams to the unassigned league."""
    institution_id, is_admin = _require_institution(current_user)
    return {
        "message": delete_league(
            session, league.league_id, institution_id, is_admin=is_admin
        )
    }


@institution_router.post("/unassign-team")
@verify_admin_or_institution
async def unassign_team_endpoint(
    team: TeamIdRef,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Move a team to the institution's 'unassigned' league without relying on a
    client-provided league id."""
    institution_id, _ = _require_institution(current_user)
    return {"message": unassign_team(session, team.team_id, institution_id)}
