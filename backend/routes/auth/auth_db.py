import logging
from datetime import timedelta

from sqlmodel import Session, select

from backend.database.db_models import AgentAPIKey, Owner, Team, TeamType
from backend.errors import InvalidCredentialsError, OwnerExistsError
from backend.routes.auth.auth_config import (
    AGENT_TOKEN_EXPIRY_DAYS,
    OWNER_TOKEN_EXPIRY_MINUTES,
    TEAM_TOKEN_EXPIRY_MINUTES,
    create_access_token,
)
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)


def owner_exists(session: Session) -> bool:
    """Whether this deployment has been claimed. Gates the setup endpoint and is
    reported by GET /config so the frontend knows to show the setup form."""
    return session.exec(select(Owner.id)).first() is not None


def mint_owner_token(owner: Owner) -> str:
    return create_access_token(
        data={"sub": owner.username, "role": "owner"},
        expires_delta=timedelta(minutes=OWNER_TOKEN_EXPIRY_MINUTES),
    )


def mint_team_token(team: Team, *, role: str = "student", expires_delta: timedelta = None) -> str:
    """Build a JWT for a team session (student or ai_agent)."""
    token_data = {
        "sub": team.name,
        "role": role,
        "team_id": team.id,
        "team_type": team.team_type.value,
        "league_id": team.league_id,
    }
    if expires_delta is None:
        expires_delta = timedelta(minutes=TEAM_TOKEN_EXPIRY_MINUTES)
    return create_access_token(data=token_data, expires_delta=expires_delta)


def create_owner(session: Session, username: str, password: str) -> str:
    """Claim an unclaimed deployment, returning a token for the new owner.

    Refuses once an owner exists — that check is the entire authorization for
    this endpoint, which is why it is safe to expose in production.
    """
    if owner_exists(session):
        raise OwnerExistsError("This deployment has already been set up")

    owner = Owner(username=username, password_hash="")
    owner.set_password(password)
    session.add(owner)
    session.commit()
    session.refresh(owner)
    logger.info(f'Deployment claimed by owner "{username}"')
    return mint_owner_token(owner)


def login(session: Session, name: str, password: str) -> dict:
    """Authenticate the owner or a team against one name+password form.

    Resolves the owner first, then a team; team names are globally unique, so it
    is one row either way. Every failure raises the same error with the same
    message, so the response never reveals which namespace the name matched.
    """
    owner = session.exec(select(Owner).where(Owner.username == name)).one_or_none()
    if owner is not None and owner.verify_password(password):
        return {
            "access_token": mint_owner_token(owner),
            "token_type": "bearer",
            "role": "owner",
        }

    team = session.exec(select(Team).where(Team.name == name)).one_or_none()
    if team is not None and team.verify_password(password):
        return {
            "access_token": mint_team_token(team),
            "token_type": "bearer",
            "role": "student",
        }

    raise InvalidCredentialsError("Invalid credentials")


def verify_agent_api_key(session: Session, api_key: str):
    """Verify agent API key and return token.

    Stays separate from /auth/login: the credential is an API key, not a name and
    password, so it cannot share the same request body.
    """
    api_key_record = session.exec(
        select(AgentAPIKey).where(
            AgentAPIKey.key == api_key, AgentAPIKey.is_active == True  # noqa: E712
        )
    ).one_or_none()

    if not api_key_record:
        raise InvalidCredentialsError("Invalid or inactive API key")

    team = api_key_record.team
    if not team or team.team_type != TeamType.AGENT:
        raise InvalidCredentialsError("API key not associated with a valid agent team")

    api_key_record.last_used = utc_now()
    session.commit()

    access_token = mint_team_token(
        team,
        role="ai_agent",
        expires_delta=timedelta(days=AGENT_TOKEN_EXPIRY_DAYS),
    )

    return {"access_token": access_token, "token_type": "bearer", "role": "ai_agent"}
