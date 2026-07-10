import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlmodel import Session

from backend.config import GAMES
from backend.database.db_models import Team
from backend.database.db_session import get_db
from backend.games.game_factory import GameFactory
from backend.routes.ai.ai_models import Hint
from backend.routes.ai.hint_service import hint_available, provide_hints
from backend.routes.auth.auth_core import (
    get_current_user,
    verify_admin_or_institution,
    verify_admin_or_student,
    verify_ai_agent_service_or_student,
    verify_any_role,
)
from backend.routes.auth.auth_db import mint_team_token
from backend.routes.institution.institution_db import get_league_by_id
from backend.routes.institution.institution_models import LeagueName
from backend.routes.institution.institution_router import _resolve_institution
from backend.routes.user.code_validation import validate_code
from backend.routes.user.signup_helpers import (
    resolve_active_league_by_token,
    team_signup_success_data,
)
from backend.routes.user.team_naming import create_school_team
from backend.routes.user.user_db import (
    allow_submission,
    assign_team_to_league,
    create_team_and_assign_to_league,
    get_all_published_results,
    get_all_published_results_for_league,
    get_all_submissions_for_league,
    get_latest_submissions_for_league,
    get_league_by_signup_token,
    get_leagues_for_user,
    get_published_result,
    get_result_by_publish_link,
    get_team_by_id,
    get_team_submission,
    get_team_submission_history,
    record_failed_submission,
    save_submission,
)
from backend.routes.user.user_models import (
    DirectLeagueSignup,
    DirectSchoolLeagueSignup,
    GameName,
    LeagueAssignRequest,
    SubmissionCode,
)
from backend.schools.providers import SchoolsProviderError, get_schools_provider
from backend.tasks.validation_task import (
    await_validation_result,
    enqueue_validation,
)
from backend.utils import get_games_names

logger = logging.getLogger(__name__)

user_router = APIRouter()

# Business failures surface via the HTTP status line, not a masked 200 envelope.
# Lookups raise domain exceptions mapped centrally in api.py: user_db's
# TeamNotFoundError / LeagueNotFoundError / ResultNotFoundError -> 404,
# TeamExistsError -> 409, LeagueExpiredError -> 410, DemoLeagueError -> 403,
# SubmissionLimitExceededError -> 429; institution_db's LeagueNotFoundError -> 404
# and InstitutionAccessError -> 403 cover the league-ownership checks; the AI
# client errors (LLMResponseError -> 502, AIRequestTimeoutError -> 504,
# NoApiKeyError -> 400) cover hint generation. Request problems the router owns
# (non-team token, unknown game, school not in list) are raised inline. Anything
# unexpected surfaces as a 500 rather than a swallowed error. Each route returns
# its payload directly; action endpoints keep a "message" carrying the outcome.


def _require_team_id(current_user: dict) -> int:
    """Reject tokens that don't carry a team_id (admin/institution tokens)."""
    team_id = current_user.get("team_id")
    if team_id is None:
        raise HTTPException(
            status_code=400, detail="This endpoint requires a team token"
        )
    return team_id


@user_router.post("/submit-agent")
@verify_ai_agent_service_or_student
async def submit_agent(
    submission: SubmissionCode,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
    generate_hint: bool = False,
):
    """Submit agent code for validation and storage.

    A submission whose code fails validation is a business failure -> HTTP 400,
    but the body still carries the hint fields next to "detail" because a hint
    is most useful exactly when validation fails.
    """
    team_name = current_user["team_name"]
    team = get_team_by_id(session, current_user["team_id"])

    if not team.league:
        raise HTTPException(
            status_code=400, detail="Team is not assigned to a league."
        )
    if team.league.name == "unassigned":
        raise HTTPException(
            status_code=400, detail="Team is not assigned to a valid league."
        )

    allow_submission(session, team.id)

    # hint_available is deterministic on recorded attempts, and nothing is
    # recorded until after validation — so checking before the (expensive)
    # validation run is equivalent and avoids wasting it on a rejected request.
    allow_hint = hint_available(session, team)
    if generate_hint and not allow_hint:
        raise HTTPException(
            status_code=429,
            detail="You are not allowed to request a hint right now",
        )

    # AST safety check runs here, before enqueue: cheap, and unsafe code
    # never reaches a worker. The "Agent code is not safe: " prefix is
    # matched by hint_context.classify_outcome — do not reword.
    is_safe, error_message = validate_code(submission.code)
    if not is_safe:
        validation_result = {
            "status": "error",
            "message": f"Agent code is not safe: {error_message}",
            "feedback": None,
            "simulation_results": None,
            "duration_ms": None,
            "traceback": None,
            "stdout": None,
        }
    else:
        logger.info(f"Enqueueing validation task for team {team_name}")
        async_result = enqueue_validation(
            code=submission.code,
            game_name=team.league.game,
            team_name=team_name,
            num_simulations=20,
        )
        # Polls the backend (no thread, no shared pubsub consumer) and maps
        # every kill/timeout/worker-loss to a clean validation failure.
        validation_result = await await_validation_result(async_result)

    hint: Hint | None = None
    if generate_hint:
        hints = await provide_hints(
            session, submission.code, validation_result, team.league.game, team_name
        )
        logger.info(f"Generated hints: {hints}")
        hint = sorted(hints, key=lambda x: x.priority)[0] if hints else None
        if hint is None:
            # No submission is recorded on this path, so the hint attempt
            # isn't consumed.
            raise HTTPException(
                status_code=502,
                detail="LLM provider failed to generate a valid hint",
            )
        allow_hint = False

    duration_ms = validation_result.get("duration_ms")

    if validation_result.get("status") == "error":
        record_failed_submission(
            session,
            team.id,
            league_id=team.league_id,
            duration_ms=duration_ms,
            hint_included=generate_hint,
        )
        return JSONResponse(
            status_code=400,
            content={
                "detail": validation_result.get("message", "Code validation failed"),
                "hint": jsonable_encoder(hint),
                "hint_available": allow_hint,
            },
        )

    submission_id = save_submission(
        session,
        submission.code,
        team.id,
        league_id=team.league_id,
        duration_ms=duration_ms,
        hint_included=generate_hint,
    )
    return {
        "submission_id": submission_id,
        "team_name": team_name,
        "results": validation_result.get("simulation_results"),
        "feedback": validation_result.get("feedback"),
        "duration_ms": duration_ms,
        "hint": hint,
        "hint_available": allow_hint,
    }


@user_router.post("/league-assign")
@verify_admin_or_student
async def assign_team_to_league_endpoint(
    league: LeagueAssignRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Assign a team to a league and return a refreshed token carrying the new league_id."""
    team_id = _require_team_id(current_user)
    logger.info(
        f'Team "{current_user["team_name"]}" about to assign to league_id={league.league_id}'
    )
    msg = assign_team_to_league(
        session, team_id, league.league_id, current_user["is_demo"]
    )
    team = get_team_by_id(session, team_id)
    role = current_user.get("role", "student")
    token_role = "ai_agent" if role == "ai_agent" else "student"
    return {
        "message": msg,
        "access_token": mint_team_token(team, role=token_role),
        "token_type": "bearer",
    }


@user_router.post("/get-published-results-for-league")
def get_published_results_for_league_endpoint(
    league: LeagueName, session: Session = Depends(get_db)
):
    """Get published results for a specific league (null when nothing is published)."""
    return get_published_result(session, league.name)


@user_router.get("/get-all-published-results-for-my-league")
@verify_any_role
async def get_all_published_results_for_my_league_endpoint(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """All published results for the league the caller is enrolled in (JWT-scoped).

    Reads `league_id` from the token to prevent cross-league leakage. Returns
    an empty list if the caller has no league assigned.
    """
    league_id = current_user.get("league_id")
    if not league_id:
        return {"all_results": [], "league_name": None, "info_markdown": ""}
    return get_all_published_results_for_league(session, league_id)


@user_router.get("/get-published-results-for-all-leagues")
def get_published_results_for_all_leagues_endpoint(session: Session = Depends(get_db)):
    """Get all published results across leagues"""
    return get_all_published_results(session)


@user_router.post("/get-game-instructions")
async def get_game_instructions(game: GameName):
    """Get instructions for a specific game"""
    if game.game_name not in GAMES:
        raise HTTPException(
            status_code=400, detail=f"Unknown game: {game.game_name}"
        )
    game_class = GameFactory.get_game_class(game.game_name)
    return {
        "starter_code": game_class.starter_code,
        "game_instructions": game_class.game_instructions,
        "reward_schema": game_class.reward_schema,
        "reward_instructions": game_class.reward_instructions,
    }


@user_router.post("/get-available-games")
async def get_available_games():
    """Get list of available games"""
    return {"games": get_games_names()}


@user_router.get("/get-all-leagues")
@verify_any_role
async def get_leagues_endpoint(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get all leagues - accessible to both admin and student roles"""
    return get_leagues_for_user(
        session, current_user.get("role"), current_user.get("institution_id")
    )


@user_router.get("/get-league-submissions/{league_id}")
@verify_admin_or_institution
async def get_league_submissions(
    league_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get latest submissions for all teams in a league.

    Restricted to the institution that owns the league; admin and the internal
    service role bypass the ownership check.
    """
    role = current_user.get("role")
    if role not in ("admin", "service"):
        institution_id, _ = _resolve_institution(current_user)
        if not institution_id:
            raise HTTPException(
                status_code=400, detail="Institution ID not found in token"
            )
        get_league_by_id(session, league_id, institution_id, is_admin=False)

    return get_latest_submissions_for_league(session, league_id)


@user_router.get("/get-all-league-submissions/{league_id}")
@verify_admin_or_institution
async def get_all_league_submissions(
    league_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get all submissions for all teams in a league with timestamps.

    Access is restricted to the institution that owns the league (admins
    bypass the ownership check). A league the caller does not own raises
    InstitutionAccessError -> 403 — never leaks cross-institution data.
    """
    institution_id, is_admin = _resolve_institution(current_user)
    if not institution_id:
        raise HTTPException(
            status_code=400, detail="Institution ID not found in token"
        )

    league = get_league_by_id(session, league_id, institution_id, is_admin=is_admin)
    result = get_all_submissions_for_league(session, league_id)
    return {
        "league_name": league.name,
        "teams": result["teams"],
        "team_ids": result["team_ids"],
    }


@user_router.get("/get-team-submission")
@verify_any_role
async def get_team_submission_endpoint(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get latest submission for the current team, scoped to current league."""
    team_id = _require_team_id(current_user)
    team = session.get(Team, team_id)
    league_id = team.league_id if team else current_user.get("league_id")
    return get_team_submission(session, team_id, league_id=league_id)


@user_router.get("/get-team-submissions")
@verify_any_role
async def get_team_submissions_endpoint(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get full submission history for the current team"""
    team_id = _require_team_id(current_user)
    return {"submissions": get_team_submission_history(session, team_id)}


@user_router.post("/direct-league-signup")
async def direct_league_signup(
    signup: DirectLeagueSignup,
    session: Session = Depends(get_db),
):
    """Create a team and directly assign it to a league using the signup token"""
    league = resolve_active_league_by_token(session, signup.signup_token)
    team = create_team_and_assign_to_league(
        session, signup.team_name, signup.password, league.id, signup.school_name
    )
    return {
        "message": (
            f"Team '{team.name}' created and assigned to league "
            f"'{league.name}' successfully!"
        ),
        **team_signup_success_data(team, league),
    }


@user_router.get("/league-info/{signup_token}")
async def get_league_by_token(
    signup_token: str,
    session: Session = Depends(get_db),
):
    """Get league information by its signup token"""
    league = get_league_by_signup_token(session, signup_token)

    data = {
        "id": league.id,
        "name": league.name,
        "game": league.game,
        "created_date": league.created_date,
        "expiry_date": league.expiry_date,
        "school_league": league.school_league,
    }

    if league.school_league:
        try:
            provider = get_schools_provider(league)
            schools = provider.list_schools() if provider else []
        except SchoolsProviderError as e:
            # Soft fallback: the signup page still renders without the list.
            logger.error(f"Schools provider error for league {league.id}: {e}")
            schools = []
        data["schools"] = schools

    return data


@user_router.post("/direct-school-league-signup")
async def direct_school_league_signup(
    signup: DirectSchoolLeagueSignup,
    session: Session = Depends(get_db),
):
    """Create a team in a school league using the server-assigned team name."""
    league = resolve_active_league_by_token(session, signup.signup_token)

    if not league.school_league:
        raise HTTPException(
            status_code=400, detail="This league is not a school league"
        )

    try:
        provider = get_schools_provider(league)
        allowed = set(provider.list_schools()) if provider else set()
    except SchoolsProviderError as e:
        # Unlike league-info there is no soft fallback: signup must not
        # proceed against an unverifiable school list.
        raise HTTPException(
            status_code=502, detail=f"School list unavailable: {str(e)}"
        )

    if signup.school_name not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"School '{signup.school_name}' is not in this league's "
                "allowed list"
            ),
        )

    team = create_school_team(session, league.id, signup.school_name, signup.password)
    return {
        "message": (
            f"Team '{team.name}' created and assigned to league "
            f"'{league.name}' successfully!"
        ),
        **team_signup_success_data(team, league),
    }


@user_router.get("/published-result/{publish_link}")
async def get_published_result_by_link(
    publish_link: str,
    session: Session = Depends(get_db),
):
    """Get a published result by its unique publish link"""
    return get_result_by_publish_link(session, publish_link)
