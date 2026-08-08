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
OWNER_TOKEN_EXPIRY_MINUTES = 360
AGENT_TOKEN_EXPIRY_DAYS = 30


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create a JWT access token with standardized timestamp handling"""
    to_encode = data.copy()
    expire = utc_now() + (
        expires_delta if expires_delta else timedelta(minutes=TEAM_TOKEN_EXPIRY_MINUTES)
    )
    to_encode.update({"exp": int(expire.timestamp())})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
