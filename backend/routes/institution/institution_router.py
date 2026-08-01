import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.database.db_models import Institution, Team, Tutorial
from backend.database.db_session import get_db
from backend.routes.auth.auth_core import (
    get_current_user,
    verify_admin_or_institution,
    verify_institution_role,
)
from backend.routes.institution.classroom_db import (
    get_classroom_concept_matrix,
    get_classroom_progress,
    get_classroom_tutorial_matrix,
    get_student_agent_submissions,
    get_student_summary,
)
from backend.routes.institution.institution_db import (
    ProtectedLeagueError,
    assign_team_to_league,
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
    get_team_by_id,
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
    SimulationResultsSubmission,
    TeamDelete,
    TeamIdRef,
    TeamLeagueAssignment,
    TeamSignup,
)
from backend.routes.tutorial.tutorial_db import (
    get_exercise_by_id,
    get_exercise_submission_history,
    get_league_tutorial_ids,
    set_league_tutorials,
)
logger = logging.getLogger(__name__)

institution_router = APIRouter()

# Business failures surface via the HTTP status line, not a masked 200 envelope.
# League/team lookups and ownership checks raise domain exceptions mapped centrally
# in api.py: LeagueNotFoundError / TeamNotFoundError / SimulationResultNotFoundError
# -> 404 (foreign resources 404 like missing ones, so responses never confirm
# another institution's ids exist), LeagueExistsError / TeamExistsError -> 409,
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


@institution_router.get("/classroom/{league_id}/progress")
@verify_admin_or_institution
async def classroom_progress_endpoint(
    league_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Per-student roster stats for one classroom: lifetime agent submission
    stats, full ranking trend, last-active across agent and exercise
    activity, and exercise completion against the classroom's tutorials."""
    institution_id, is_admin = _require_institution(current_user)
    league = get_league_by_id(session, league_id, institution_id, is_admin=is_admin)
    return get_classroom_progress(session, league)


@institution_router.get("/classroom/{league_id}/tutorial-matrix")
@verify_admin_or_institution
async def classroom_tutorial_matrix_endpoint(
    league_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Student x exercise status grid for each tutorial attached to the
    classroom. Untouched cells are omitted from the payload."""
    institution_id, is_admin = _require_institution(current_user)
    league = get_league_by_id(session, league_id, institution_id, is_admin=is_admin)
    return get_classroom_tutorial_matrix(session, league)


@institution_router.get("/classroom/{league_id}/concept-matrix")
@verify_admin_or_institution
async def classroom_concept_matrix_endpoint(
    league_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Student x concept mastery grid for the classroom: which concepts the
    class has, and which students are struggling with each. Cells for concepts
    a student hasn't reached are omitted from the payload."""
    institution_id, is_admin = _require_institution(current_user)
    league = get_league_by_id(session, league_id, institution_id, is_admin=is_admin)
    return get_classroom_concept_matrix(session, league)


@institution_router.get("/student/{team_id}/summary")
@verify_admin_or_institution
async def student_summary_endpoint(
    team_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Drill-down header for one student: identity, lifetime agent stats with
    ranking trend, and per-exercise tutorial status in their classroom."""
    institution_id, is_admin = _require_institution(current_user)
    team = get_team_by_id(session, team_id, institution_id, is_admin=is_admin)
    return get_student_summary(session, team)


@institution_router.get("/student/{team_id}/agent-submissions")
@verify_admin_or_institution
async def student_agent_submissions_endpoint(
    team_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """One student's full validated agent submission history (code included),
    oldest first."""
    institution_id, is_admin = _require_institution(current_user)
    team = get_team_by_id(session, team_id, institution_id, is_admin=is_admin)
    return get_student_agent_submissions(session, team)


@institution_router.get("/student/{team_id}/exercise-submissions")
@verify_admin_or_institution
async def student_exercise_submissions_endpoint(
    team_id: int,
    exercise_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """One student's submission history for one exercise, newest first, with
    code and per-test results. Ownership is team-level: the exercise need not
    be attached to the student's current league, so history survives league
    moves and tutorial detachment."""
    institution_id, is_admin = _require_institution(current_user)
    team = get_team_by_id(session, team_id, institution_id, is_admin=is_admin)
    exercise = get_exercise_by_id(session, exercise_id)
    tutorial = session.get(Tutorial, exercise.tutorial_id)
    return {
        "team": {"id": team.id, "name": team.name},
        "exercise": {
            "id": exercise.id,
            "title": exercise.title,
            "tutorial_id": exercise.tutorial_id,
            "tutorial_title": tutorial.title if tutorial else None,
        },
        "submissions": get_exercise_submission_history(
            session, team.id, exercise.id
        ),
    }


def _subscription_payload(institution: Institution) -> dict:
    """Display-only subscription + contact fields for the given institution.

    Stripe object IDs are not exposed — only fields the institution needs to
    see. Shared by the subscription and home endpoints.
    """
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


@institution_router.get("/subscription")
@verify_institution_role
async def get_subscription_endpoint(
    session: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return the logged-in institution's subscription + contact details."""
    institution_id, _ = _require_institution(current_user)

    institution = session.get(Institution, institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    return _subscription_payload(institution)


@institution_router.get("/home")
@verify_institution_role
async def get_home_endpoint(
    session: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Payload backing the institution/teacher home page: one card per
    league/classroom (team count, game, attached tutorial titles, signup
    link) plus the same subscription summary as /subscription."""
    institution_id, _ = _require_institution(current_user)

    institution = session.get(Institution, institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    data = _subscription_payload(institution)
    data["classrooms"] = get_classroom_summaries(session, institution_id)
    return data


@institution_router.post("/save-simulation-results")
@verify_admin_or_institution
async def save_simulation_results_endpoint(
    submission: SimulationResultsSubmission,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Persist simulation results computed by the in-browser (Pyodide) runner.

    The browser runs the games — the admin/institution user triggering a run
    already has access to every team's code — so the server only checks
    ownership and shape before storing. The response mirrors what the old
    worker-side run-simulation endpoint returned, so the frontend result flow
    downstream of a run is unchanged. `player_feedback` is deliberately not
    round-tripped: it was never persisted, the browser keeps its own copy.
    """
    institution_id, is_admin = _require_institution(current_user)

    league = get_league_by_id(
        session, submission.league_id, institution_id, is_admin=is_admin
    )

    if league.name == "unassigned":
        raise ProtectedLeagueError(
            "Cannot save simulation results for the 'unassigned' league"
        )

    # save_simulation_results silently skips names it can't resolve; on a
    # client bug that would store a run with missing rows, so reject instead.
    league_team_names = set(
        session.exec(select(Team.name).where(Team.league_id == league.id)).all()
    )
    unknown = sorted(set(submission.total_points) - league_team_names)
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Results reference unknown team(s): {', '.join(unknown)}",
        )

    feedback = submission.feedback
    sim_result = save_simulation_results(
        session,
        league.id,
        institution_id,
        {
            "num_simulations": submission.num_simulations,
            "total_points": submission.total_points,
            "table": submission.table,
        },
        submission.custom_rewards,
        feedback_str=(feedback if isinstance(feedback, str) else None),
        feedback_json=(json.dumps(feedback) if isinstance(feedback, dict) else None),
        is_admin=is_admin,
    )

    response_data = {
        "league_name": league.name,
        "id": sim_result.id,
        "total_points": submission.total_points,
        "num_simulations": submission.num_simulations,
        "requested_simulations": submission.requested_simulations,
        "capped": submission.capped,
        "timestamp": sim_result.timestamp,
        "rewards": submission.custom_rewards,
        "table": submission.table,
        "strategies": submission.strategies,
    }
    if feedback is not None:
        response_data["feedback"] = feedback

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


@institution_router.post("/team-password-reset")
@verify_institution_role
async def team_password_reset_endpoint(
    team: TeamIdRef,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Generate a shareable one-time password-reset link for a team."""
    institution_id, _ = _require_institution(current_user)
    result = generate_team_password_reset(session, team.team_id, institution_id)
    return {
        "message": (
            f"Password reset link generated for '{result['team_name']}'"
        ),
        "reset_token": result["reset_token"],
        "team_name": result["team_name"],
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
