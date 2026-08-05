import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.database.db_session import get_db
from backend.routes.auth import auth_config
from backend.routes.auth.auth_config import (
    EXEC_TOKEN_EXPIRY_SECONDS,
    create_execution_token,
)
from backend.routes.auth.auth_core import get_current_user, verify_any_role
from backend.routes.auth.auth_db import (
    get_admin_token,
    get_competitions,
    get_institution_token,
    get_team_token,
    verify_agent_api_key,
)
from backend.routes.auth.auth_models import (
    AdminLogin,
    AgentLogin,
    CompetitionsResponse,
    ExecutionTokenResponse,
    InstitutionLogin,
    TeamLogin,
    TokenResponse,
)

logger = logging.getLogger(__name__)

auth_router = APIRouter()

# Invalid credentials raise InvalidCredentialsError, mapped to HTTP 401 by the
# handler registered in api.py. Any other exception surfaces as a 500. This
# keeps each route a single expression instead of a per-route try/except.


@auth_router.get("/competitions", response_model=CompetitionsResponse)
def list_competitions(session: Session = Depends(get_db)):
    """Public endpoint listing competitions for the student login picker."""
    return CompetitionsResponse(competitions=get_competitions(session))


@auth_router.post("/admin-login", response_model=TokenResponse)
def admin_login(login: AdminLogin, session: Session = Depends(get_db)):
    """Authenticate an administrator and issue an access token."""
    logger.info(f'Admin login attempt for username: "{login.username}"')
    return get_admin_token(session, login.username, login.password)


@auth_router.post("/team-login", response_model=TokenResponse)
def team_login(credentials: TeamLogin, session: Session = Depends(get_db)):
    """Authenticate a team and issue an access token."""
    return get_team_token(session, credentials.name, credentials.password)


@auth_router.post("/institution-login", response_model=TokenResponse)
def institution_login(login: InstitutionLogin, session: Session = Depends(get_db)):
    """Authenticate an institution and issue an access token."""
    logger.info(f'Institution login attempt for name: "{login.name}"')
    return get_institution_token(session, login.name, login.password)


@auth_router.post("/agent-login", response_model=TokenResponse)
def agent_login(credentials: AgentLogin, session: Session = Depends(get_db)):
    """Authenticate an agent via API key and issue an access token."""
    return verify_agent_api_key(session, credentials.api_key)


@auth_router.post("/execution-token", response_model=ExecutionTokenResponse)
@verify_any_role
async def execution_token(current_user: dict = Depends(get_current_user)):
    """Exchange a session token for a short-lived execution token.

    The browser presents this to the exercise-fallback Lambda's Function URL
    (direct call, no API in the execution leg). Signed with the dedicated
    EXEC_JWT_SECRET — see create_execution_token for why it is never
    SECRET_KEY. 503 when the secret isn't configured (direct path disabled)."""
    # Read through the module so tests (and a future secret rotation) see
    # the live value, not an import-time copy.
    if not auth_config.EXEC_JWT_SECRET:
        raise HTTPException(
            status_code=503, detail="Execution tokens are not configured"
        )
    sub = (
        current_user.get("team_name")
        or current_user.get("institution_name")
        or current_user["role"]
    )
    return ExecutionTokenResponse(
        token=create_execution_token(sub, current_user["role"]),
        expires_in=EXEC_TOKEN_EXPIRY_SECONDS,
    )
