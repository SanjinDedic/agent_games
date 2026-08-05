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
# Just long enough to reach the Lambda and start the run (exp is checked
# before execution, not during). Deliberately too short to read out of a
# devtools pane and replay; the Lambda-side verifier additionally rejects any
# exp more than exec_token.MAX_TTL_SECONDS in the future, so even a token
# minted with a stolen secret can't be long-lived.
EXEC_TOKEN_EXPIRY_SECONDS = 10

# Dedicated secret for execution tokens (direct browser→Lambda fallback
# calls). NEVER SECRET_KEY: the Lambda verifies these in the same process
# that runs student code, and process memory is readable there — this secret
# is the only one whose theft grants nothing beyond invoking the sandbox the
# caller could already invoke. Optional: unset disables /auth/execution-token
# (dev without the direct path).
EXEC_JWT_SECRET = os.getenv("EXEC_JWT_SECRET")


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


def create_execution_token(sub: str, role: str) -> str:
    """Short-lived token the browser presents to the fallback Lambda's
    Function URL. Signed with EXEC_JWT_SECRET; the Lambda-side verifier
    (backend/lambda_fallback/exercise_snippet/exec_token.py, stdlib-only) requires the
    ``scope: "exec"`` claim, so a stolen execution token opens nothing else.
    ``test_exec_token.py`` pins mint/verify parity."""
    if not EXEC_JWT_SECRET:
        raise RuntimeError("EXEC_JWT_SECRET is not set")
    expire = utc_now() + timedelta(seconds=EXEC_TOKEN_EXPIRY_SECONDS)
    payload = {
        "sub": sub,
        "role": role,
        "scope": "exec",
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, EXEC_JWT_SECRET, algorithm=ALGORITHM)
