"""Provider-agnostic AI client abstraction.

Each provider subclasses AIClient and implements one high-level operation:
a structured completion that takes a system prompt, a user payload, and a
Pydantic schema, and returns a validated instance of that schema. Provider
quirks (request body shape, response envelope, structured-output mechanism,
schema dialect) stay inside the subclass — callers never see them.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 60.0
KEY_CHECK_TIMEOUT = 10.0

T = TypeVar("T", bound=BaseModel)


# --- Error taxonomy (shared by all providers) ---


class AIClientError(Exception):
    """Base error for AI client failures."""


class NoApiKeyError(AIClientError):
    """No API key is configured for the requested provider."""


class UnknownProviderError(AIClientError):
    """The requested provider has no registered client."""


class LLMResponseError(AIClientError):
    """The provider returned an unusable response (HTTP error, bad JSON, schema mismatch)."""


class AIRequestTimeoutError(AIClientError):
    """The provider did not respond within the request timeout."""


# --- Schema normalization ---

# Value constraints that strict structured-output modes (OpenAI strict
# json_schema, Anthropic output_config.format) reject or ignore. Safe to strip:
# Pydantic re-validates the parsed response, so they are still enforced.
_UNSUPPORTED_SCHEMA_KEYS = frozenset(
    {
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "pattern",
        "minItems",
        "maxItems",
        "default",
    }
)


def prepare_json_schema(schema: Any) -> Any:
    """Normalize a Pydantic-generated JSON schema for strict provider modes.

    Strict modes require additionalProperties=false and every property listed
    in `required`, and reject value constraints like minLength/maximum.
    """
    if isinstance(schema, list):
        return [prepare_json_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    cleaned: Dict[str, Any] = {}
    for key, value in schema.items():
        if key in _UNSUPPORTED_SCHEMA_KEYS:
            continue
        if key == "properties" and isinstance(value, dict):
            # Property *names* must not be filtered, only their sub-schemas.
            cleaned[key] = {
                name: prepare_json_schema(sub) for name, sub in value.items()
            }
        else:
            cleaned[key] = prepare_json_schema(value)
    if cleaned.get("type") == "object" and isinstance(cleaned.get("properties"), dict):
        cleaned["additionalProperties"] = False
        cleaned["required"] = list(cleaned["properties"].keys())
    return cleaned


# --- Client ABC ---


class AIClient(ABC):
    """One instance per (provider, api_key) pair. Stateless between calls."""

    provider: ClassVar[str]

    def __init__(self, api_key: str):
        self.api_key = api_key

    @abstractmethod
    async def complete_structured(
        self,
        *,
        system: str,
        user: str,
        schema: Type[T],
        model: str,
        temperature: Optional[float] = None,
        reasoning_effort: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> T:
        """Run a single system+user completion and return a validated `schema` instance."""

    @abstractmethod
    def _headers(self) -> Dict[str, str]:
        """Auth/content headers for this provider."""

    @abstractmethod
    def _models_url(self) -> str:
        """Cheap authenticated GET endpoint used to validate the key."""

    async def check_key(self) -> bool:
        """Live key check: True when the models endpoint accepts the key."""
        try:
            async with httpx.AsyncClient(timeout=KEY_CHECK_TIMEOUT) as client:
                response = await client.get(self._models_url(), headers=self._headers())
        except httpx.TimeoutException as e:
            raise AIRequestTimeoutError(f"{self.provider} request timed out") from e
        return response.status_code == 200

    # --- Shared HTTP/parsing helpers ---

    async def _post_json(self, url: str, body: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(url, headers=self._headers(), json=body)
        except httpx.TimeoutException as e:
            raise AIRequestTimeoutError(f"{self.provider} request timed out") from e
        except httpx.HTTPError as e:
            logger.exception(f"{self.provider} connection failed: {repr(e)}")
            raise LLMResponseError(f"{self.provider} connection failed: {e}") from e
        if response.status_code != 200:
            logger.error(
                "%s returned HTTP %s: %s",
                self.provider,
                response.status_code,
                response.text[:500],
            )
            raise LLMResponseError(
                f"{self.provider} returned HTTP {response.status_code}"
            )
        return response.json()

    def _validate_content(self, content: str, schema: Type[T]) -> T:
        try:
            return schema.model_validate_json(content)
        except ValidationError as e:
            raise LLMResponseError(
                f"{self.provider} response did not match schema: {e}"
            ) from e
