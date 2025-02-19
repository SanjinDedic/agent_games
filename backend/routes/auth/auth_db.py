import logging
import os
from datetime import datetime, timedelta

import pytz
from sqlmodel import Session, create_engine, select

from backend.database.db_config import get_database_url
from backend.database.db_models import Admin, AgentAPIKey, Team, TeamType
from backend.routes.auth.auth_core import create_access_token

logger = logging.getLogger(__name__)


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid"""

    pass


class RateLimitExceededError(Exception):
    """Raised when API rate limit is exceeded"""

    pass


AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


def get_db():
    """Database session dependency"""
    engine = create_engine(get_database_url())
    with Session(engine) as session:
        yield session


def get_team_token(session: Session, team_name: str, team_password: str):
    """Get authentication token for team login"""
    team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()

    if not team:
        raise InvalidCredentialsError(f"Team '{team_name}' not found")

    if not team.verify_password(team_password):
        raise InvalidCredentialsError("Invalid team password")

    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={"sub": team_name, "role": "student"}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


def get_admin_token(session: Session, username: str, password: str):
    """Get authentication token for admin login"""
    admin = session.exec(select(Admin).where(Admin.username == username)).one_or_none()

    if not admin or not admin.verify_password(password):
        raise InvalidCredentialsError("Invalid credentials")

    access_token_expires = timedelta(minutes=20)
    access_token = create_access_token(
        data={"sub": "admin", "role": "admin"}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


def verify_agent_api_key(session: Session, api_key: str):
    """Verify agent API key and return token"""
    try:
        # Find the API key record
        api_key_record = session.exec(
            select(AgentAPIKey).where(
                AgentAPIKey.key == api_key, AgentAPIKey.is_active == True
            )
        ).one_or_none()

        if not api_key_record:
            raise InvalidCredentialsError("Invalid or inactive API key")

        # Get associated team
        team = api_key_record.team
        if not team or team.team_type != TeamType.AGENT:
            raise InvalidCredentialsError(
                "API key not associated with a valid agent team"
            )

        # Update last used timestamp
        api_key_record.last_used = datetime.now(AUSTRALIA_SYDNEY_TZ)
        session.commit()

        # Create long-lived token for agent
        access_token_expires = timedelta(days=30)
        access_token = create_access_token(
            data={
                "sub": team.name,
                "role": "ai_agent",
                "team_name": team.name,
            },
            expires_delta=access_token_expires,
        )

        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        logger.error(f"Error verifying agent API key: {str(e)}")
        raise InvalidCredentialsError("Error verifying API key")
