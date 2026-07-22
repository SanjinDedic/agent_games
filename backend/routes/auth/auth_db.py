import logging
import os
from datetime import timedelta

from sqlmodel import Session, select

from backend.database.db_models import (
    Admin,
    AgentAPIKey,
    Institution,
    InstitutionSubscription,
    Team,
    TeamType,
)
from backend.routes.auth.auth_config import (
    ADMIN_TOKEN_EXPIRY_MINUTES,
    AGENT_TOKEN_EXPIRY_DAYS,
    INSTITUTION_TOKEN_EXPIRY_MINUTES,
    TEAM_TOKEN_EXPIRY_MINUTES,
    create_access_token,
)
from backend.time_utils import ensure_utc, utc_now

logger = logging.getLogger(__name__)


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid"""

    pass


class RateLimitExceededError(Exception):
    """Raised when API rate limit is exceeded"""

    pass


def get_competitions(session: Session):
    """Active competition institutions for the public login picker.

    Teacher accounts are excluded: classroom students log in through their
    league's shareable /join/<token> page, never through this list.
    """
    institutions = session.exec(
        select(Institution)
        .join(InstitutionSubscription)
        .where(InstitutionSubscription.subscription_active == True)
        .where(Institution.name != "Demo Institution")
        .where(Institution.is_teacher == False)
    ).all()
    return [{"name": inst.name, "icon": inst.icon} for inst in institutions]


def mint_team_token(team: Team, *, role: str = "student", expires_delta: timedelta = None) -> str:
    """Build a JWT for a team session (student or ai_agent)."""
    token_data = {
        "sub": team.name,
        "role": role,
        "team_id": team.id,
        "team_type": team.team_type.value,
        "is_demo": team.is_demo,
        "institution_id": team.institution_id,
        "league_id": team.league_id,
        # Students of a teacher account see classroom/student wording; requires
        # a session-attached team (relationship lazy-loads the institution).
        "is_teacher": bool(team.institution.is_teacher) if team.institution else False,
    }
    if expires_delta is None:
        expires_delta = timedelta(minutes=TEAM_TOKEN_EXPIRY_MINUTES)
    return create_access_token(data=token_data, expires_delta=expires_delta)


def get_team_token(session: Session, team_name: str, team_password: str):
    """Get authentication token for team login.

    Team names are only unique within an institution (see Team's composite
    constraints), so a name can be shared across institutions. Login has no
    institution context, so we match on name + password: try every team with
    this name and authenticate the one whose password verifies. Two teams with
    an identical name *and* password is the only ambiguous case; the first match
    wins, which is acceptable and no worse than the old global-unique rule.
    """
    teams = session.exec(select(Team).where(Team.name == team_name)).all()

    if not teams:
        raise InvalidCredentialsError(f"Team '{team_name}' not found")

    for team in teams:
        if team.verify_password(team_password):
            access_token = mint_team_token(team)
            return {"access_token": access_token, "token_type": "bearer"}

    raise InvalidCredentialsError("Invalid team password")


def get_admin_token(session: Session, username: str, password: str):
    """Get authentication token for admin login"""
    admin = session.exec(select(Admin).where(Admin.username == username)).one_or_none()

    if not admin or not admin.verify_password(password):
        raise InvalidCredentialsError("Invalid credentials")

    access_token = create_access_token(
        data={"sub": "admin", "role": "admin", "institution_id": 1},
        expires_delta=timedelta(minutes=ADMIN_TOKEN_EXPIRY_MINUTES),
    )

    return {"access_token": access_token, "token_type": "bearer"}


# Update this part in get_institution_token in auth_db.py
def get_institution_token(session: Session, institution_name: str, password: str):
    """Get authentication token for institution login"""
    institution = session.exec(
        select(Institution).where(Institution.name == institution_name)
    ).one_or_none()

    if not institution:
        raise InvalidCredentialsError(f"Institution '{institution_name}' not found")

    if not institution.verify_password(password):
        raise InvalidCredentialsError("Invalid password")

    # Subscription state lives on the 1:1 InstitutionSubscription record.
    subscription = institution.subscription

    # Check if subscription is active (missing record == no active subscription)
    if subscription is None or not subscription.subscription_active:
        raise InvalidCredentialsError("Institution subscription is not active")

    if ensure_utc(subscription.subscription_expiry) < utc_now():
        # Update subscription_active to False
        subscription.subscription_active = False
        session.add(subscription)
        session.commit()
        raise InvalidCredentialsError("Institution subscription has expired")

    access_token = create_access_token(
        data={
            "sub": institution_name,
            "role": "institution",
            "institution_id": institution.id,
            "institution_name": institution_name,
            "is_teacher": institution.is_teacher,
        },
        expires_delta=timedelta(minutes=INSTITUTION_TOKEN_EXPIRY_MINUTES),
    )

    return {"access_token": access_token, "token_type": "bearer"}


def verify_agent_api_key(session: Session, api_key: str):
    """Verify agent API key and return token"""
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
    api_key_record.last_used = utc_now()
    session.commit()

    access_token = mint_team_token(
        team,
        role="ai_agent",
        expires_delta=timedelta(days=AGENT_TOKEN_EXPIRY_DAYS),
    )

    return {"access_token": access_token, "token_type": "bearer"}
