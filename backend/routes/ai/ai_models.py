from typing import Optional

from pydantic import BaseModel


class APIKeysResponse(BaseModel):
    """Response with masked API keys"""

    openai_api_key: str = ""


class UpdateAPIKeysRequest(BaseModel):
    """Request to update API keys. None means 'do not change'."""

    openai_api_key: Optional[str] = None


class ValidateAPIKeyRequest(BaseModel):
    """Request to validate a specific provider's key"""

    provider: str
    api_key: Optional[str] = None  # If None, validate the stored key
