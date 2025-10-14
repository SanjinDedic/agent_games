import logging

from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.models_api import ResponseModel
from backend.routes.auth.auth_db import (
    InvalidCredentialsError,
    get_admin_token,
    get_db,
    get_institution_token,
    get_team_token,
    verify_agent_api_key,
)
from backend.routes.auth.auth_models import (
    AdminLogin,
    AgentLogin,
    InstitutionLogin,
    TeamLogin,
)

logger = logging.getLogger(__name__)

auth_router = APIRouter()


@auth_router.post("/admin-login", response_model=ResponseModel)
def admin_login(login: AdminLogin, session: Session = Depends(get_db)):
    """
    Endpoint for administrator login
    """
    logger.info(f'Admin login attempt for username: "{login.username}"')
    try:
        token = get_admin_token(session, login.username, login.password)
        return ResponseModel(status="success", message="Login successful", data=token)
    except InvalidCredentialsError as e:
        return ResponseModel(status="failed", message=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during admin login: {str(e)}")
        return ResponseModel(status="failed", message="An unexpected error occurred")


@auth_router.post("/team-login", response_model=ResponseModel)
def team_login(credentials: TeamLogin, session: Session = Depends(get_db)):
    """
    Endpoint for team login
    """
    try:
        team_token = get_team_token(session, credentials.name, credentials.password)
        logger.info(f"Generated token for team {credentials.name}: {team_token}")
        print(f"Generated token for team {credentials.name}: {team_token}")
        return ResponseModel(
            status="success", message="Login successful", data=team_token
        )
    except InvalidCredentialsError as e:
        return ResponseModel(status="failed", message=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during team login: {str(e)}")
        return ResponseModel(status="failed", message="An unexpected error occurred")


@auth_router.post("/institution-login", response_model=ResponseModel)
def institution_login(login: InstitutionLogin, session: Session = Depends(get_db)):
    """
    Endpoint for institution login
    """
    logger.info(f'Institution login attempt for name: "{login.name}"')
    try:
        print(f'Institution login attempt for name: "{login.name}"')
        token = get_institution_token(session, login.name, login.password)
        print(f"Generated token for institution {login.name}: {token}")
        return ResponseModel(status="success", message="Login successful", data=token)
    except InvalidCredentialsError as e:
        return ResponseModel(status="failed", message=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during institution login: {str(e)}")
        return ResponseModel(status="failed", message="An unexpected error occurred")


# Add this new endpoint with your other login endpoints
@auth_router.post("/agent-login", response_model=ResponseModel)
def agent_login(credentials: AgentLogin, session: Session = Depends(get_db)):
    """Endpoint for agent login via API key"""
    try:
        agent_token = verify_agent_api_key(session, credentials.api_key)
        return ResponseModel(
            status="success", message="Login successful", data=agent_token
        )
    except InvalidCredentialsError as e:
        return ResponseModel(status="failed", message=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during agent login: {str(e)}")
        return ResponseModel(status="failed", message="An unexpected error occurred")
