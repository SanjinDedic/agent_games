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

# JWT constants
ALGORITHM = "HS256"
SECRET_KEY = os.getenv("SECRET_KEY", "test_secret_key_for_tests")
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")

# Token expiry durations
TEAM_TOKEN_EXPIRY_MINUTES = 180
ADMIN_TOKEN_EXPIRY_MINUTES = 360
INSTITUTION_TOKEN_EXPIRY_MINUTES = 360
AGENT_TOKEN_EXPIRY_DAYS = 30
DEMO_TOKEN_EXPIRY_MINUTES = 90
SERVICE_TOKEN_EXPIRY_DAYS = 365


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create a JWT access token with standardized timestamp handling"""
    to_encode = data.copy()
    expire = datetime.now(AUSTRALIA_SYDNEY_TZ) + (
        expires_delta if expires_delta else timedelta(minutes=TEAM_TOKEN_EXPIRY_MINUTES)
    )
    # Store expiration as UTC timestamp
    to_encode.update({"exp": int(expire.timestamp())})

    if SECRET_KEY is None:
        raise ValueError(
            "SECRET_KEY is not set. Set it in environment variables or .env file."
        )

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_service_token() -> str:
    """Create a long-lived JWT token for service-to-service communication"""
    service_data = {"sub": "service", "role": "service"}
    expires_delta = timedelta(days=SERVICE_TOKEN_EXPIRY_DAYS)
    return create_access_token(service_data, expires_delta)
