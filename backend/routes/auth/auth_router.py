import logging

from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.database.db_session import get_db
from backend.routes.auth.auth_db import (
    get_admin_token,
    get_institution_token,
    get_institution_names,
    get_team_token,
    verify_agent_api_key,
)
from backend.routes.auth.auth_models import (
    AdminLogin,
    AgentLogin,
    InstitutionLogin,
    InstitutionsResponse,
    TeamLogin,
    TokenResponse,
)

logger = logging.getLogger(__name__)

auth_router = APIRouter()

# Invalid credentials raise InvalidCredentialsError, mapped to HTTP 401 by the
# handler registered in api.py. Any other exception surfaces as a 500. This
# keeps each route a single expression instead of a per-route try/except.


@auth_router.get("/institutions", response_model=InstitutionsResponse)
def list_institutions(session: Session = Depends(get_db)):
    """Public endpoint to list institution names for the login selector."""
    return InstitutionsResponse(institutions=get_institution_names(session))


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
