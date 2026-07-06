"""Anthropic Messages API client (raw HTTP, consistent with the other providers).

Structured output uses `output_config.format` with a JSON schema — the API
then guarantees the first content block is text containing valid JSON.
Supported on Claude Fable 5, Opus 4.8, Sonnet 5, and Haiku 4.5 (plus legacy
Opus 4.5/4.1).
"""

import logging
from typing import Dict, Optional, Type

from backend.routes.ai.clients.base import (
    AIClient,
    LLMResponseError,
    T,
    prepare_json_schema,
)

logger = logging.getLogger(__name__)

# Maps OpenAI-style reasoning_effort values onto Anthropic's output_config.effort.
_EFFORT_MAP = {"minimal": "low", "low": "low", "medium": "medium", "high": "high"}


class AnthropicClient(AIClient):
    provider = "anthropic"
    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"
    # max_tokens is mandatory on /v1/messages; generous default since our
    # schemas produce small outputs and unspent budget costs nothing.
    DEFAULT_MAX_TOKENS = 16000

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }

    def _models_url(self) -> str:
        return f"{self.BASE_URL}/models"

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
        body = {
            "model": model,
            "max_tokens": max_tokens or self.DEFAULT_MAX_TOKENS,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": prepare_json_schema(schema.model_json_schema()),
                }
            },
        }
        if temperature is not None:
            # Rejected with a 400 on Opus 4.7+/Sonnet 5/Fable 5 — only pass it
            # when targeting older models.
            body["temperature"] = temperature
        if reasoning_effort is not None:
            body["output_config"]["effort"] = _EFFORT_MAP.get(
                reasoning_effort, reasoning_effort
            )

        envelope = await self._post_json(f"{self.BASE_URL}/messages", body)
        if envelope.get("stop_reason") == "refusal":
            raise LLMResponseError(
                f"{self.provider} declined the request (stop_reason=refusal)"
            )
        try:
            content = next(
                block["text"]
                for block in envelope["content"]
                if block.get("type") == "text"
            )
        except (KeyError, StopIteration, TypeError) as e:
            raise LLMResponseError(
                f"Malformed {self.provider} response envelope: {e}"
            ) from e
        return self._validate_content(content, schema)
