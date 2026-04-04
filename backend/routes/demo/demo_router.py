import logging
import re
from datetime import datetime, timedelta

import pytz
from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.models_api import ErrorResponseModel, ResponseModel
from backend.routes.auth.auth_config import DEMO_TOKEN_EXPIRY_MINUTES, create_access_token
from backend.database.db_session import get_db
from backend.routes.demo.demo_db import create_demo_user, ensure_demo_leagues_exist
from backend.routes.demo.demo_models import DemoLaunchRequestWithUser
from backend.utils import get_games_names

logger = logging.getLogger(__name__)
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")

demo_router = APIRouter()


@demo_router.post("/launch_demo", response_model=ResponseModel)
async def launch_demo(
    request: DemoLaunchRequestWithUser = None,
    session: Session = Depends(get_db),
):
    """Create a demo user with temporary credentials and return a token"""
    try:
        # Validate username if provided
        username = "Guest"
        email = None

        if request:
            # Basic validation (more detailed validation is in the pydantic model)
            username = request.username
            email = request.email

        # Ensure demo leagues exist for all games
        demo_leagues = ensure_demo_leagues_exist(session)

        # Create a new demo user with the provided username
        demo_user = create_demo_user(session, username, email)

        # Create a token valid for DEMO_TOKEN_EXPIRY_MINUTES minutes
        expires_delta = timedelta(minutes=DEMO_TOKEN_EXPIRY_MINUTES)
        token_data = {
            "sub": demo_user.name,
            "role": "student",
            "is_demo": True,
            "exp_time": DEMO_TOKEN_EXPIRY_MINUTES,
        }
        access_token = create_access_token(token_data, expires_delta)

        # Get available games for the demo
        available_games = get_games_names()

        return ResponseModel(
            status="success",
            message=f"Demo access granted for {DEMO_TOKEN_EXPIRY_MINUTES} minutes",
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "username": demo_user.name,
                "expires_in_minutes": DEMO_TOKEN_EXPIRY_MINUTES,
                "expires_at": (
                    datetime.now(AUSTRALIA_SYDNEY_TZ) + expires_delta
                ).isoformat(),
                "available_games": available_games,
                "demo_leagues": [league.name for league in demo_leagues],
            },
        )
    except ValueError as e:
        logger.warning(f"Validation error in demo launch: {str(e)}")
        return ErrorResponseModel(status="error", message=f"Invalid input: {str(e)}")
    except Exception as e:
        logger.error(f"Error launching demo: {str(e)}")
        return ErrorResponseModel(
            status="error", message=f"Failed to launch demo mode: {str(e)}"
        )
