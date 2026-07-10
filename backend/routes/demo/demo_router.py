from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.database.db_session import get_db
from backend.routes.auth.auth_config import DEMO_TOKEN_EXPIRY_MINUTES
from backend.routes.auth.auth_db import mint_team_token
from backend.routes.demo.demo_db import create_demo_user, ensure_demo_leagues_exist
from backend.routes.demo.demo_models import DemoLaunchRequestWithUser, DemoLaunchResponse
from backend.time_utils import utc_now
from backend.utils import get_games_names

demo_router = APIRouter()

# Request validation (username/email rules) lives in the pydantic model, so bad
# input is a 422 before the body runs. A missing "unassigned" league is a seed-time
# invariant, not user input, so it surfaces as a 500 rather than a masked 200. The
# payload is small and fixed, so the success body is modelled (like the auth tokens).


@demo_router.post("/launch_demo", response_model=DemoLaunchResponse)
async def launch_demo(
    request: DemoLaunchRequestWithUser = None,
    session: Session = Depends(get_db),
):
    """Create a demo user with temporary credentials and return a token."""
    username = request.username if request else "Guest"
    email = request.email if request else None

    demo_leagues = ensure_demo_leagues_exist(session)
    demo_user = create_demo_user(session, username, email)

    expires_delta = timedelta(minutes=DEMO_TOKEN_EXPIRY_MINUTES)
    access_token = mint_team_token(demo_user, expires_delta=expires_delta)

    return DemoLaunchResponse(
        access_token=access_token,
        username=demo_user.name,
        expires_in_minutes=DEMO_TOKEN_EXPIRY_MINUTES,
        expires_at=(utc_now() + expires_delta).isoformat(),
        available_games=get_games_names(),
        demo_leagues=[league.name for league in demo_leagues],
    )
