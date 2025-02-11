import base64
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, List, Union

import pytz
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.routes.auth.auth_config import ALGORITHM, SECRET_KEY, create_access_token

logger = logging.getLogger(__name__)

AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Define valid roles
ROLE_ADMIN = "admin"
ROLE_STUDENT = "student"
ROLE_INSTITUTION = "institution"
ROLE_AI_AGENT = "ai_agent"
ROLE_SERVICE = "service"

ALL_ROLES = [ROLE_ADMIN, ROLE_STUDENT, ROLE_INSTITUTION, ROLE_AI_AGENT, ROLE_SERVICE]


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(AUSTRALIA_SYDNEY_TZ) + (
        expires_delta if expires_delta else timedelta(minutes=15)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


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

            roles = [allowed_roles] if isinstance(allowed_roles, str) else allowed_roles
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


def create_service_token() -> str:
    """Create a long-lived JWT token for service-to-service communication"""
    service_data = {"sub": "service", "role": ROLE_SERVICE}
    # Create a token that expires far in the future (e.g., 1 year)
    expires = datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=365)
    return create_access_token(service_data, timedelta(days=365))


def get_current_user(token: str = Depends(oauth2_scheme)):
    logger.info(f"Attempting to validate token: {token[:20]}...")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        team_name: str = payload.get("sub")
        user_role: str = payload.get("role")
        exp_timestamp = payload.get("exp")

        # Check expiration using timestamp comparison
        current_timestamp = datetime.now(AUSTRALIA_SYDNEY_TZ).timestamp()
        if exp_timestamp is None or current_timestamp > exp_timestamp:
            logger.error("Token has expired")
            raise HTTPException(status_code=401, detail="Token has expired")

        if team_name is None or user_role not in ALL_ROLES:
            logger.error(
                f"Invalid token content - team_name: {team_name}, role: {user_role}"
            )
            raise HTTPException(status_code=401, detail="Invalid token")

        return {"team_name": team_name, "role": user_role}
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
