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

from backend.config import ALGORITHM, SECRET_KEY

logger = logging.getLogger(__name__)

AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Define valid roles
ROLE_ADMIN = "admin"
ROLE_STUDENT = "student"
ROLE_INSTITUTION = "institution"
ROLE_AI_AGENT = "ai_agent"

ALL_ROLES = [ROLE_ADMIN, ROLE_STUDENT, ROLE_INSTITUTION, ROLE_AI_AGENT]


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


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
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current_user from kwargs since FastAPI injects it
            current_user = kwargs.get("current_user")
            if not current_user or not isinstance(current_user, dict):
                raise HTTPException(status_code=401, detail="Invalid authentication")

            roles = [allowed_roles] if isinstance(allowed_roles, str) else allowed_roles
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

# All roles except admin
verify_non_admin = verify_role([ROLE_STUDENT, ROLE_INSTITUTION, ROLE_AI_AGENT])

# Verification for all roles
verify_any_role = verify_role(ALL_ROLES)


def get_current_user(token: str = Depends(oauth2_scheme)):
    logger.info(f"Attempting to validate token: {token[:20]}...")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"Token payload: {payload}")
        team_name: str = payload.get("sub")
        user_role: str = payload.get("role")

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
