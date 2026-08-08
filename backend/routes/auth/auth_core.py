import base64
import logging

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from backend.routes.auth.auth_config import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,  # noqa: F401  re-exported: callers import it from here
)
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Three roles. `admin` runs the deployment (leagues, teams, keys, simulations);
# `student` and `ai_agent` are the two kinds of team session, split only by how
# they authenticate — a password versus an API key.
ROLE_ADMIN = "admin"
ROLE_STUDENT = "student"
ROLE_AI_AGENT = "ai_agent"

ALL_ROLES = [ROLE_ADMIN, ROLE_STUDENT, ROLE_AI_AGENT]
TEAM_ROLES = (ROLE_STUDENT, ROLE_AI_AGENT)


def get_current_user(token: str = Depends(oauth2_scheme)):
    """Decode and validate a bearer token into a plain claims dict."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        user_role: str = payload.get("role")
        exp_timestamp = payload.get("exp")

        current_timestamp = utc_now().timestamp()
        if exp_timestamp is None or current_timestamp > exp_timestamp:
            logger.error("Token has expired")
            raise HTTPException(status_code=401, detail="Token has expired")

        if sub is None or user_role not in ALL_ROLES:
            logger.error(f"Invalid token content - sub: {sub}, role: {user_role}")
            raise HTTPException(status_code=401, detail="Invalid token")

        user_data = {"role": user_role}

        if user_role in TEAM_ROLES:
            user_data["team_name"] = sub
            user_data["team_id"] = payload.get("team_id")
            user_data["team_type"] = payload.get("team_type")
            user_data["league_id"] = payload.get("league_id")
        else:
            user_data["admin_name"] = sub

        return user_data

    except JWTError as e:
        logger.error(f"JWT Error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")


# Guards are dependencies, not decorators. The decorator form read
# kwargs["current_user"], so a route had to declare both the decorator and a
# Depends(get_current_user) parameter: forgetting the Depends silently 401'd,
# and forgetting the decorator silently removed the guard. As a dependency the
# guard *is* what produces current_user, so neither mistake is possible.


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Allow only the deployment's admin account."""
    if current_user["role"] != ROLE_ADMIN:
        raise HTTPException(
            status_code=403, detail="This operation requires the admin role"
        )
    return current_user


def require_team(current_user: dict = Depends(get_current_user)) -> dict:
    """Allow a team session (student or ai_agent) and guarantee a team_id.

    Absorbs the old user_router._require_team_id check: a token that claims a
    team role without a team_id is malformed, not merely unauthorized.
    """
    if current_user["role"] not in TEAM_ROLES:
        raise HTTPException(
            status_code=403, detail="This operation requires a team account"
        )
    if not current_user.get("team_id"):
        raise HTTPException(status_code=400, detail="Team ID not found in token")
    return current_user


def require_agent(current_user: dict = Depends(get_current_user)) -> dict:
    """Allow only an API-key agent session.

    Narrower than require_team on purpose: the /agent routes are the
    machine-driven surface, and a student password must not reach them.
    """
    if current_user["role"] != ROLE_AI_AGENT:
        raise HTTPException(
            status_code=403, detail="This operation requires an agent account"
        )
    if not current_user.get("team_id"):
        raise HTTPException(status_code=400, detail="Team ID not found in token")
    return current_user


def require_any(current_user: dict = Depends(get_current_user)) -> dict:
    """Allow any authenticated caller; the route decides what to do per role."""
    return current_user


def encode_id(id: int) -> str:
    id_bytes = str(id).encode("utf-8")
    encoded_id = base64.urlsafe_b64encode(id_bytes).decode("utf-8")
    return encoded_id


def decode_id(encoded_id: str) -> int:
    id_bytes = base64.urlsafe_b64decode(encoded_id)
    decoded_id = int(id_bytes.decode("utf-8"))
    return decoded_id
