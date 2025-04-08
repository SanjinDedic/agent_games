import os
from datetime import datetime, timedelta

import pytz
from dotenv import load_dotenv
from jose import jwt

# Load environment variables from root .env file
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
load_dotenv(os.path.join(project_root, ".env"))

# Constants
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
# Use a default secret key for testing if none is provided
# This should NEVER be used in production
SECRET_KEY = os.getenv("SECRET_KEY", "test_secret_key_for_development_only")
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


def create_service_token() -> str:
    """Create a long-lived JWT token for service-to-service communication"""
    service_data = {"sub": "service", "role": "service"}
    # Explicitly set token to expire in 1 year
    expires_delta = timedelta(days=365)
    return create_access_token(service_data, expires_delta)


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create a JWT access token with standardized timestamp handling"""
    to_encode = data.copy()
    expire = datetime.now(AUSTRALIA_SYDNEY_TZ) + (
        expires_delta if expires_delta else timedelta(minutes=15)
    )
    # Store expiration as UTC timestamp
    to_encode.update({"exp": int(expire.timestamp())})

    # Ensure SECRET_KEY is not None before encoding
    if SECRET_KEY is None:
        raise ValueError(
            "SECRET_KEY is not set. Set it in environment variables or .env file."
        )

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
