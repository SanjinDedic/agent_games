import logging
from datetime import datetime, timedelta

import pytz
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.config import DEMO_TOKEN_EXPIRY
from backend.database.db_models import Team
from backend.models_api import ErrorResponseModel, ResponseModel
from backend.routes.auth.auth_config import create_access_token
from backend.routes.auth.auth_core import get_current_user
from backend.routes.auth.auth_db import get_db
from backend.routes.demo.demo_db import (
    assign_user_to_demo_league,
    create_demo_user,
    get_or_create_demo_league,
)
from backend.routes.demo.demo_models import DemoGameSelectRequest
from backend.utils import get_games_names

logger = logging.getLogger(__name__)
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")

demo_router = APIRouter()


# TODO: Create a get_demo_token function in backend/routes/demo/demo_db.py
# TODO: Explore auth_core and get_current_user in backend/routes/auth/auth_core.py see if you need to make a similar function


@demo_router.post("/launch_demo", response_model=ResponseModel)
async def launch_demo(
    session: Session = Depends(get_db),
):
    """Create a demo user with temporary credentials and return a token"""
    try:
        # Create a new demo user with a random password
        demo_user, demo_password = create_demo_user(session)

        # Create a token valid for DEMO_TOKEN_EXPIRY minutes
        expires_delta = timedelta(minutes=DEMO_TOKEN_EXPIRY)
        token_data = {
            "sub": demo_user.name,
            "role": "student",
            "is_demo": True,
            "exp_time": DEMO_TOKEN_EXPIRY,
        }
        access_token = create_access_token(token_data, expires_delta)

        # Get available games for the demo
        available_games = get_games_names()

        return ResponseModel(
            status="success",
            message=f"Demo access granted for {DEMO_TOKEN_EXPIRY} minutes",
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "username": demo_user.name,
                "expires_in_minutes": DEMO_TOKEN_EXPIRY,
                "expires_at": (
                    datetime.now(AUSTRALIA_SYDNEY_TZ) + expires_delta
                ).isoformat(),
                "available_games": available_games,
            },
        )
    except Exception as e:
        logger.error(f"Error launching demo: {str(e)}")
        return ErrorResponseModel(
            status="error", message=f"Failed to launch demo mode: {str(e)}"
        )


@demo_router.post("/select_game", response_model=ResponseModel)
async def select_game(
    request: DemoGameSelectRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Select a game for demo play and create/assign to appropriate league"""
    try:
        # Verify user is a demo user
        if not current_user.get("is_demo", False):
            return ErrorResponseModel(
                status="error",
                message="Game selection is only available for demo users",
            )

        # Get user record
        user = session.exec(
            select(Team).where(Team.name == current_user["team_name"])
        ).first()

        if not user:
            return ErrorResponseModel(status="error", message="User not found")

        # Get or create a demo league for the selected game
        demo_league = get_or_create_demo_league(session, request.game_name)

        # Assign user to the demo league
        assign_user_to_demo_league(session, user.id, demo_league.id)

        return ResponseModel(
            status="success",
            message=f"Demo game {request.game_name} selected",
            data={
                "league_id": demo_league.id,
                "league_name": demo_league.name,
                "game": demo_league.game,
            },
        )
    except Exception as e:
        logger.error(f"Error selecting demo game: {str(e)}")
        return ErrorResponseModel(
            status="error", message=f"Failed to select demo game: {str(e)}"
        )
