"""Provider registry + factory.

Adding a provider: implement an AIClient subclass and add it to the tuple
below — key management, key validation, and the services pick it up from
CLIENT_REGISTRY automatically.
"""

from typing import Dict, Type

from sqlmodel import Session

from backend.routes.ai.ai_db import get_stored_key
from backend.routes.ai.clients.anthropic_client import AnthropicClient
from backend.routes.ai.clients.base import (
    AIClient,
    NoApiKeyError,
    UnknownProviderError,
)
from backend.routes.ai.clients.google_client import GoogleClient
from backend.routes.ai.clients.openai_client import OpenAIClient

CLIENT_REGISTRY: Dict[str, Type[AIClient]] = {
    cls.provider: cls for cls in (OpenAIClient, AnthropicClient, GoogleClient)
}


def get_client_class(provider: str) -> Type[AIClient]:
    try:
        return CLIENT_REGISTRY[provider]
    except KeyError:
        raise UnknownProviderError(f"Unknown provider: {provider}") from None


def get_ai_client(session: Session, provider: str) -> AIClient:
    """Build a client for `provider` using the key stored in the database."""
    client_class = get_client_class(provider)
    api_key = get_stored_key(session, provider)
    if not api_key:
        raise NoApiKeyError(f"{provider} API key is not configured")
    return client_class(api_key)
