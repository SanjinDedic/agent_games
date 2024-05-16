from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timedelta
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from passlib.context import CryptContext

import base64


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now() + expires_delta if expires_delta else datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        team_name: str = payload.get("sub")
        user_role: str = payload.get("role")
        if team_name is None or user_role not in ["student", "admin"]:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"team_name": team_name, "role": user_role}

def encode_id(id: int) -> str:
    id_bytes = str(id).encode('utf-8')
    encoded_id = base64.urlsafe_b64encode(id_bytes).decode('utf-8')
    return encoded_id

def decode_id(encoded_id: str) -> int:
    id_bytes = base64.urlsafe_b64decode(encoded_id)
    id = int(id_bytes.decode('utf-8'))
    return id
