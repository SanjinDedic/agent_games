import os
from datetime import datetime, timedelta

import pytz
from dotenv import load_dotenv
from jose import jwt

load_dotenv()

# Constants
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
SECRET_KEY = os.getenv("SECRET_KEY")
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


# Token creation functions
def create_service_token() -> str:
    """Create a long-lived JWT token for service-to-service communication"""
    service_data = {"sub": "service", "role": "service"}
    # Create a token that expires far in the future (e.g., 1 year)
    expires = datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=365)
    return create_access_token(service_data, timedelta(days=365))


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create a JWT access token with the provided data and expiry"""
    to_encode = data.copy()
    expire = datetime.now(AUSTRALIA_SYDNEY_TZ) + (
        expires_delta if expires_delta else timedelta(minutes=15)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
