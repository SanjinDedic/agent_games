import os
from datetime import datetime, timedelta
import pytz
from jose import jwt
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(backend_dir / '.env')

ALGORITHM = "HS256"
SECRET_KEY = os.getenv("SECRET_KEY")

AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")

def create_service_token() -> str:
    """Create a long-lived JWT token for service-to-service communication"""
    service_data = {
        "sub": "service",
        "role": "service"
    }
    # Create a token that expires far in the future (e.g., 1 year)
    expires = datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=365)
    return create_access_token(service_data, timedelta(days=365))

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(AUSTRALIA_SYDNEY_TZ) + (
        expires_delta if expires_delta else timedelta(minutes=15)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt