import base64
import logging
from functools import wraps
from typing import Callable, List, Union

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from backend.routes.auth.auth_config import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_service_token,
)
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Define valid roles
ROLE_ADMIN = "admin"
ROLE_STUDENT = "student"
ROLE_INSTITUTION = "institution"
ROLE_AI_AGENT = "ai_agent"
ROLE_SERVICE = "service"

ALL_ROLES = [ROLE_ADMIN, ROLE_STUDENT, ROLE_INSTITUTION, ROLE_AI_AGENT, ROLE_SERVICE]


def verify_role(allowed_roles: Union[str, List[str]]):
    """
    Decorator factory to verify if the current user has one of the allowed roles.
    Always allows service role.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user or not isinstance(current_user, dict):
                raise HTTPException(status_code=401, detail="Invalid authentication")

            roles = [allowed_roles] if isinstance(allowed_roles, str) else list(allowed_roles)
            roles.append(ROLE_SERVICE)  # Always allow service role

            if current_user["role"] not in roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"This operation requires one of these roles: {roles}",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Single role verification decorators
verify_admin_role = verify_role(ROLE_ADMIN)
verify_student_role = verify_role(ROLE_STUDENT)
verify_institution_role = verify_role(ROLE_INSTITUTION)
verify_ai_agent_role = verify_role(ROLE_AI_AGENT)

# Common multi-role verification decorators
verify_admin_or_student = verify_role([ROLE_ADMIN, ROLE_STUDENT])
verify_admin_or_institution = verify_role([ROLE_ADMIN, ROLE_INSTITUTION])
verify_institution_or_student = verify_role([ROLE_INSTITUTION, ROLE_STUDENT])
verify_admin_or_ai_agent = verify_role([ROLE_ADMIN, ROLE_AI_AGENT])
verify_ai_agent_service_or_student = verify_role(
    [ROLE_AI_AGENT, ROLE_SERVICE, ROLE_STUDENT]
)

# All roles except admin
verify_non_admin = verify_role([ROLE_STUDENT, ROLE_INSTITUTION, ROLE_AI_AGENT])

# Verification for all roles
verify_any_role = verify_role(ALL_ROLES)


def get_current_user(token: str = Depends(oauth2_scheme)):
    logger.info(f"Attempting to validate token: {token[:20]}...")
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

        user_data = {
            "role": user_role,
            "institution_id": payload.get("institution_id"),
        }

        if user_role in (ROLE_STUDENT, ROLE_AI_AGENT):
            user_data["team_name"] = sub
            user_data["team_id"] = payload.get("team_id")
            user_data["team_type"] = payload.get("team_type")
            user_data["is_demo"] = payload.get("is_demo", False)
            user_data["league_id"] = payload.get("league_id")
        elif user_role == ROLE_INSTITUTION:
            user_data["institution_name"] = sub

        return user_data

    except JWTError as e:
        logger.error(f"JWT Error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")


def encode_id(id: int) -> str:
    id_bytes = str(id).encode("utf-8")
    encoded_id = base64.urlsafe_b64encode(id_bytes).decode("utf-8")
    return encoded_id


def decode_id(encoded_id: str) -> int:
    id_bytes = base64.urlsafe_b64decode(encoded_id)
    decoded_id = int(id_bytes.decode("utf-8"))
    return decoded_id
