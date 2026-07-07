"""OpenAI chat-completions client.

Also serves as the base for any provider exposing an OpenAI-compatible
endpoint (Google Gemini, Groq, Mistral, DeepSeek, xAI, ...): subclass and
override `provider` and `BASE_URL`.
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


class OpenAIClient(AIClient):
    provider = "openai"
    BASE_URL = "https://api.openai.com/v1"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
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
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": prepare_json_schema(schema.model_json_schema()),
                },
            },
        }
        if temperature is not None:
            body["temperature"] = temperature
        if reasoning_effort is not None:
            body["reasoning_effort"] = reasoning_effort
        if max_tokens is not None:
            body["max_completion_tokens"] = max_tokens

        envelope = await self._post_json(f"{self.BASE_URL}/chat/completions", body)
        try:
            content = envelope["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMResponseError(
                f"Malformed {self.provider} response envelope: {e}"
            ) from e
        return self._validate_content(content, schema)
