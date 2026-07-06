"""Google Gemini via Google's OpenAI-compatible endpoint.

The chat-completions surface (including json_schema response_format and
reasoning_effort) is translated by Google, so the whole implementation is
the OpenAI client pointed at a different base URL.
"""

from backend.routes.ai.clients.openai_client import OpenAIClient


class GoogleClient(OpenAIClient):
    provider = "google"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
