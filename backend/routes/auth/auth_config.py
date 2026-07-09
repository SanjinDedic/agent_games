import os
from datetime import timedelta

from dotenv import load_dotenv
from jose import jwt

from backend.time_utils import utc_now

# Load environment variables from root .env file
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
load_dotenv(os.path.join(project_root, ".env"))

# JWT constants
ALGORITHM = "HS256"
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Set it in environment variables or .env file."
    )
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
    expire = utc_now() + (
        expires_delta if expires_delta else timedelta(minutes=TEAM_TOKEN_EXPIRY_MINUTES)
    )
    to_encode.update({"exp": int(expire.timestamp())})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_service_token() -> str:
    """Create a long-lived JWT token for service-to-service communication"""
    service_data = {"sub": "service", "role": "service"}
    expires_delta = timedelta(days=SERVICE_TOKEN_EXPIRY_DAYS)
    return create_access_token(service_data, expires_delta)
