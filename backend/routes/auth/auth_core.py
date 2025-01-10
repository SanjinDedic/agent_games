import base64
import logging
from datetime import datetime, timedelta

import pytz
from config import ALGORITHM, SECRET_KEY
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)


AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = (
        datetime.now(AUSTRALIA_SYDNEY_TZ) + expires_delta
        if expires_delta
        else datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(minutes=15)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# routes/auth/auth_core.py


def get_current_user(token: str = Depends(oauth2_scheme)):
    logger.info(f"Attempting to validate token: {token[:20]}...")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"Token payload: {payload}")
        team_name: str = payload.get("sub")
        user_role: str = payload.get("role")
        print(f"team_name: {team_name}, role: {user_role}")
        if team_name is None or user_role not in ["student", "admin"]:
            logger.error(
                f"Invalid token content - team_name: {team_name}, role: {user_role}"
            )
            print(f"Invalid token content - team_name: {team_name}, role: {user_role}")
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
