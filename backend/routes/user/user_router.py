import json
import logging
import os
from typing import Dict, Optional

import httpx
from config import ROOT_DIR
from database.db_models import Team
from docker_utils.scripts.docker_simulation import run_docker_simulation
from fastapi import APIRouter, Depends, HTTPException
from games.game_factory import GameFactory
from models_api import ErrorResponseModel, ResponseModel
from routes.admin.admin_models import LeagueName
from routes.auth.auth_core import (
    get_current_user,
    verify_admin_or_student,
    verify_any_role,
    verify_student_role,
)
from routes.auth.auth_db import get_db
from routes.user.user_db import (
    SubmissionLimitExceededError,
    allow_submission,
    assign_team_to_league,
    get_all_leagues,
    get_all_published_results,
    get_published_result,
    get_team,
    save_submission,
)
from routes.user.user_models import GameName, LeagueAssignRequest, SubmissionCode
from sqlmodel import Session
from utils import get_games_names

logger = logging.getLogger(__name__)

user_router = APIRouter()


@user_router.post("/submit-agent", response_model=ResponseModel)
@verify_student_role
async def submit_agent(
    submission: SubmissionCode,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Submit agent code for validation and storage"""
    team_name = current_user["team_name"]
    team = get_team(session, team_name)

    try:
        logger.info(f"Sending submission to validation server for team {team_name}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8001/validate",
                json={
                    "code": submission.code,
                    "game_name": team.league.game if team.league else "greedy_pig",
                    "team_name": team_name,
                    "num_simulations": 100,
                },
                timeout=30.0,
            )

        if response.status_code != 200:
            return ErrorResponseModel(
                status="error", message=f"Validation failed: {response.text}"
            )

        validation_result = response.json()
        if validation_result.get("status") == "error":
            return ErrorResponseModel(
                status="error",
                message=validation_result.get("message", "Code validation failed"),
            )

    except Exception as e:
        logger.error(f"Error during validation: {e}")
        return ErrorResponseModel(
            status="error", message=f"An error occurred during validation: {str(e)}"
        )

    if not team.league:
        return ErrorResponseModel(
            status="error", message="Team is not assigned to a league."
        )

    if team.league.name == "unassigned":
        return ErrorResponseModel(
            status="error", message="Team is not assigned to a valid league."
        )

    try:
        if not allow_submission(session, team.id):
            return ErrorResponseModel(
                status="error", message="You can only make 5 submissions per minute."
            )
    except SubmissionLimitExceededError as e:
        return ErrorResponseModel(status="error", message=str(e))

    league_folder = (
        team.league.folder.lstrip("/")
        if team.league.folder
        else f"leagues/user/{team.league.name}"
    )
    file_path = os.path.join(
        ROOT_DIR, "games", team.league.game, league_folder, f"{team_name}.py"
    )

    with open(file_path, "w") as file:
        file.write(submission.code)

    try:
        submission_id = save_submission(session, submission.code, team.id)
        return ResponseModel(
            status="success",
            message=f"Code submitted successfully. Submission ID: {submission_id}",
            data={
                "results": validation_result.get("simulation_results"),
                "team_name": team_name,
                "feedback": validation_result.get("feedback"),
            },
        )
    except Exception as e:
        logger.error(f"Error saving submission: {e}")
        return ErrorResponseModel(
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
@verify_admin_or_student
async def get_leagues_endpoint(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get all leagues - accessible to both admin and student roles"""
    logger.info("Received request for get-all-leagues")
    logger.info(f"Current user data: {current_user}")

    try:
        # Reuse existing admin function
        leagues = get_all_leagues(session)
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
