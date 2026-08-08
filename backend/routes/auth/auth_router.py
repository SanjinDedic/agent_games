import logging

from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.database.db_session import get_db
from backend.routes.auth.auth_db import create_admin, login, verify_agent_api_key
from backend.routes.auth.auth_models import (
    AgentLogin,
    Login,
    AdminSetup,
    TokenResponse,
)

logger = logging.getLogger(__name__)

auth_router = APIRouter()

# Invalid credentials raise InvalidCredentialsError, mapped to HTTP 401 by the
# handler registered in api.py; a second setup attempt raises AdminExistsError ->
# 409. Any other exception surfaces as a 500. This keeps each route a single
# expression instead of a per-route try/except.


@auth_router.post("/setup", response_model=TokenResponse)
def setup_admin(request: AdminSetup, session: Session = Depends(get_db)):
    """Claim a fresh deployment by creating its single admin account.

    Unauthenticated by necessity — there is no account to authenticate with yet.
    Safe in production because it refuses once an admin exists, so the window is
    exactly one call. GET /config reports setup_required so the frontend knows
    whether to offer this or the login form.
    """
    return TokenResponse(
        access_token=create_admin(session, request.name, request.password),
        role="admin",
    )


@auth_router.post("/login", response_model=TokenResponse)
def login_endpoint(credentials: Login, session: Session = Depends(get_db)):
    """Authenticate the admin or a team and issue an access token.

    Deliberately does not log the submitted name: a failed attempt is often a
    password typed into the name field.
    """
    return login(session, credentials.name, credentials.password)


@auth_router.post("/agent-login", response_model=TokenResponse)
def agent_login(credentials: AgentLogin, session: Session = Depends(get_db)):
    """Authenticate an agent via API key and issue an access token."""
    return verify_agent_api_key(session, credentials.api_key)
