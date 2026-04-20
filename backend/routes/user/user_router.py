import logging

import httpx
from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.config import get_service_url
from backend.database.db_models import League
from backend.games.game_factory import GameFactory
from backend.models_api import ErrorResponseModel, ResponseModel
from backend.routes.auth.auth_core import (
    get_current_user,
    verify_admin_or_institution,
    verify_admin_or_student,
    verify_ai_agent_service_or_student,
    verify_any_role,
)
from backend.database.db_session import get_db
from backend.routes.institution.institution_db import (
    InstitutionAccessError,
    LeagueNotFoundError,
    get_league_by_id,
)
from backend.routes.institution.institution_models import LeagueName
from backend.routes.institution.institution_router import _resolve_institution
from backend.routes.user.user_db import (
    SubmissionLimitExceededError,
    TeamNotFoundError,
    allow_submission,
    assign_team_to_league,
    create_team_and_assign_to_league,
    get_all_leagues,
    get_leagues_for_user,
    get_all_published_results,
    get_all_submissions_for_league,
    get_latest_submissions_for_league,
    get_league_by_signup_token,
    get_published_result,
    get_team,
    get_team_submission,
    save_submission,
    get_result_by_publish_link,
)
from backend.routes.user.user_models import (
    DirectLeagueSignup,
    DirectSchoolLeagueSignup,
    GameName,
    LeagueAssignRequest,
    SubmissionCode,
)
from backend.routes.user.signup_helpers import (
    resolve_active_league_by_token,
    team_signup_success_data,
)
from backend.routes.user.team_naming import create_school_team
from backend.schools.providers import SchoolsProviderError, get_schools_provider
from backend.utils import get_games_names

logger = logging.getLogger(__name__)

user_router = APIRouter()


@user_router.post("/submit-agent", response_model=ResponseModel)
@verify_ai_agent_service_or_student
async def submit_agent(
    submission: SubmissionCode,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Submit agent code for validation and storage"""
    team_name = current_user["team_name"]
    try:
        team = get_team(session, team_name)
    except TeamNotFoundError:
        return ResponseModel(status="error", message=f"Team '{team_name}' not found")

    # Check league assignment first
    if not team.league:
        return ResponseModel(
            status="error", message="Team is not assigned to a league."
        )

    if team.league.name == "unassigned":
        return ResponseModel(
            status="error", message="Team is not assigned to a valid league."
        )

    try:
        if not allow_submission(session, team.id):
            return ResponseModel(
                status="error", message="You can only make 5 submissions per minute."
            )
    except SubmissionLimitExceededError as e:
        return ResponseModel(status="error", message=str(e))

    try:
        # Get environment-aware URL for validator
        validator_url = get_service_url("validator", "validate")
        logger.info(f"Sending submission to validation server for team {team_name}")
        logger.info(f"Using validator URL: {validator_url}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                validator_url,
                json={
                    "code": submission.code,
                    "game_name": team.league.game,
                    "team_name": team_name,
                    "num_simulations": 20,
                },
                timeout=20.0,
            )

        if response.status_code != 200:
            return ResponseModel(
                status="error", message=f"Validation failed: {response.text}"
            )

        validation_result = response.json()
        if validation_result.get("status") == "error":
            return ResponseModel(
                status="error",
                message=validation_result.get("message", "Code validation failed"),
            )

    except Exception as e:
        logger.error(f"Error or timeout during validation {e}")
        return ResponseModel(
            status="error", message=f"An error occurred during validation: {str(e)}"
        )

    try:
        submission_id = save_submission(session, submission.code, team.id)
        return ResponseModel(
            status="success",
            message=f"Code submitted successfully. Submission ID: {submission_id}",
            data={
                "team_name": team_name,
                "results": validation_result.get("simulation_results"),
                "feedback": validation_result.get("feedback"),
            },
        )
    except Exception as e:
        logger.error(f"Error saving submission: {e}")
        return ResponseModel(
            status="error",
            message=f"An error occurred while saving the submission: {str(e)}",
        )


@user_router.post("/league-assign", response_model=ResponseModel)
@verify_admin_or_student
async def assign_team_to_league_endpoint(
    league: LeagueAssignRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Assign a team to a league"""
    team_name = current_user["team_name"]
    logger.info(f'Team Name "{team_name} about to assign to league "{league.name}"')
    try:
        msg = assign_team_to_league(session, team_name, league.name)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        logger.error(
            f'Error assigning team "{team_name}" to league "{league.name}": {str(e)}'
        )
        return ErrorResponseModel(
            status="error",
            message="An error occurred while assigning team to league" + str(e),
        )


@user_router.post("/get-published-results-for-league", response_model=ResponseModel)
def get_published_results_for_league_endpoint(
    league: LeagueName, session: Session = Depends(get_db)
):
    """Get published results for a specific league"""
    try:
        published_results = get_published_result(session, league.name)
        if published_results:
            return ResponseModel(
                status="success",
                message="Published results retrieved successfully",
                data=published_results,
            )
        return ResponseModel(
            status="success",
            message="No published results found for the specified league",
            data=None,
        )
    except Exception as e:
        return ErrorResponseModel(
            status="error",
            message="An error occurred while retrieving published results " + str(e),
        )


@user_router.get("/get-published-results-for-all-leagues", response_model=ResponseModel)
def get_published_results_for_all_leagues_endpoint(session: Session = Depends(get_db)):
    """Get all published results across leagues"""
    try:
        published_results = get_all_published_results(session)
        if published_results:
            return ResponseModel(
                status="success",
                message="Published results retrieved successfully",
                data=published_results,
            )
        return ResponseModel(
            status="success",
            message="No published results found",
            data=None,
        )
    except Exception as e:
        logger.error(f"Error retrieving all published results: {str(e)}")
        return ErrorResponseModel(
            status="error",
            message="An error occurred while retrieving published results " + str(e),
        )


@user_router.post("/get-game-instructions", response_model=ResponseModel)
async def get_game_instructions(game: GameName):
    """Get instructions for a specific game"""
    try:
        game_class = GameFactory.get_game_class(game.game_name)
        return ResponseModel(
            status="success",
            message="Game instructions retrieved successfully",
            data={
                "starter_code": game_class.starter_code,
                "game_instructions": game_class.game_instructions,
            },
        )
    except Exception as e:
        return ErrorResponseModel(
            status="error", message=f"An error occurred: {str(e)}"
        )


@user_router.post("/get-available-games", response_model=ResponseModel)
async def get_available_games():
    """Get list of available games"""
    try:
        game_names = get_games_names()
        return ResponseModel(
            status="success",
            message="Available games retrieved successfully",
            data={"games": game_names},
        )
    except Exception as e:
        return ErrorResponseModel(
            status="error", message=f"An error occurred: {str(e)}"
        )


@user_router.get("/get-all-leagues", response_model=ResponseModel)
@verify_any_role
async def get_leagues_endpoint(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get all leagues - accessible to both admin and student roles"""
    logger.info("Received request for get-all-leagues")
    logger.info(f"Current user data: {current_user}")

    try:
        role = current_user.get("role")
        institution_id = current_user.get("institution_id")
        if role == "admin":
            institution_id = 1

        leagues = get_leagues_for_user(session, role, institution_id)
        return ResponseModel(
            status="success",
            message="Leagues retrieved successfully",
            data=leagues,
        )
    except Exception as e:
        logger.error(f"Error retrieving leagues: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve leagues: {str(e)}"
        )


@user_router.get("/get-league-submissions/{league_id}", response_model=ResponseModel)
@verify_any_role
async def get_league_submissions(
    league_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get latest submissions for all teams in a league"""
    try:
        submissions = get_latest_submissions_for_league(session, league_id)
        return ResponseModel(
            status="success",
            message="Submissions retrieved successfully",
            data=submissions,
        )
    except Exception as e:
        logger.error(f"Error retrieving submissions: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve submissions: {str(e)}"
        )


@user_router.get("/get-all-league-submissions/{league_id}", response_model=ResponseModel)
@verify_admin_or_institution
async def get_all_league_submissions(
    league_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get all submissions for all teams in a league with timestamps.

    Access is restricted to the institution that owns the league (admins
    bypass the ownership check). Returns 'error' status for leagues the
    caller does not own or that do not exist — never leaks cross-institution
    data.
    """
    try:
        institution_id, is_admin = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        try:
            league = get_league_by_id(
                session, league_id, institution_id, is_admin=is_admin
            )
        except LeagueNotFoundError:
            return ErrorResponseModel(
                status="error", message=f"League {league_id} not found"
            )
        except InstitutionAccessError:
            return ErrorResponseModel(
                status="error",
                message="You don't have permission to access this league",
            )

        submissions = get_all_submissions_for_league(session, league_id)
        return ResponseModel(
            status="success",
            message="All submissions retrieved successfully",
            data={"league_name": league.name, "teams": submissions},
        )
    except Exception as e:
        logger.error(f"Error retrieving all submissions: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve submissions: {str(e)}"
        )


@user_router.get("/get-team-submission", response_model=ResponseModel)
@verify_any_role
async def get_team_submission_endpoint(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get latest submission for the current team"""
    team_name = current_user["team_name"]
    try:
        submission_data = get_team_submission(session, team_name)
        return ResponseModel(
            status="success",
            message="Submission retrieved successfully",
            data=submission_data,
        )
    except Exception as e:
        logger.error(f"Error retrieving submission: {e}")
        return ResponseModel(
            status="error",
            message=f"Failed to retrieve submission: {str(e)}",
            data={"code": None},
        )


@user_router.post("/direct-league-signup", response_model=ResponseModel)
async def direct_league_signup(
    signup: DirectLeagueSignup,
    session: Session = Depends(get_db),
):
    """Create a team and directly assign it to a league using the signup token"""
    try:
        league, error = resolve_active_league_by_token(session, signup.signup_token)
        if error:
            return ErrorResponseModel(status="error", message=error)

        team = create_team_and_assign_to_league(
            session, signup.team_name, signup.password, league.id, signup.school_name
        )

        return ResponseModel(
            status="success",
            message=f"Team '{team.name}' created and assigned to league '{league.name}' successfully!",
            data=team_signup_success_data(team, league),
        )
    except Exception as e:
        logger.error(f"Error in direct league signup: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to complete signup: {str(e)}"
        )


@user_router.get("/league-info/{signup_token}", response_model=ResponseModel)
async def get_league_by_token(
    signup_token: str,
    session: Session = Depends(get_db),
):
    """Get league information by its signup token"""
    try:
        league = get_league_by_signup_token(session, signup_token)

        if not league:
            return ErrorResponseModel(
                status="error", message="Invalid signup link or league not found"
            )

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
                logger.error(f"Schools provider error for league {league.id}: {e}")
                schools = []
            data["schools"] = schools

        return ResponseModel(
            status="success",
            message="League information retrieved successfully",
            data=data,
        )
    except Exception as e:
        logger.error(f"Error retrieving league by token: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve league information: {str(e)}"
        )


@user_router.post("/direct-school-league-signup", response_model=ResponseModel)
async def direct_school_league_signup(
    signup: DirectSchoolLeagueSignup,
    session: Session = Depends(get_db),
):
    """Create a team in a school league using the server-assigned team name."""
    try:
        league, error = resolve_active_league_by_token(session, signup.signup_token)
        if error:
            return ErrorResponseModel(status="error", message=error)

        if not league.school_league:
            return ErrorResponseModel(
                status="error", message="This league is not a school league"
            )

        try:
            provider = get_schools_provider(league)
        except SchoolsProviderError as e:
            return ErrorResponseModel(
                status="error", message=f"School list unavailable: {str(e)}"
            )

        allowed = set(provider.list_schools()) if provider else set()
        if signup.school_name not in allowed:
            return ErrorResponseModel(
                status="error",
                message=(
                    f"School '{signup.school_name}' is not in this league's "
                    "allowed list"
                ),
            )

        team = create_school_team(
            session, league.id, signup.school_name, signup.password
        )

        return ResponseModel(
            status="success",
            message=(
                f"Team '{team.name}' created and assigned to league "
                f"'{league.name}' successfully!"
            ),
            data=team_signup_success_data(team, league),
        )
    except Exception as e:
        logger.error(f"Error in direct school-league signup: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to complete signup: {str(e)}"
        )


@user_router.get("/published-result/{publish_link}", response_model=ResponseModel)
async def get_published_result_by_link(
    publish_link: str,
    session: Session = Depends(get_db),
):
    """Get a published result by its unique publish link"""
    try:
        result = get_result_by_publish_link(session, publish_link)
        return ResponseModel(
            status="success",
            message="Published result retrieved successfully",
            data=result,
        )
    except Exception as e:
        logger.error(f"Error retrieving published result: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve published result: {str(e)}"
        )
