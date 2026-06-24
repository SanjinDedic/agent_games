
import httpx, logging
from pydantic import ValidationError
from sqlmodel import Session

from backend.routes.ai.ai_db import get_stored_key
from backend.routes.ai.hint_prompt import SYSTEM_PROMPT
from backend.routes.ai.hint_context import build_hint_context_from_response
from backend.routes.ai.ai_models import HintResponse, Hint

class HintServiceError(Exception):
    """Base error for plagiarism service failures."""  # REVIEW: copy-paste — docstring says "plagiarism", should be "hint".


class NoApiKeyError(HintServiceError):
    """OpenAI API key is not configured in the database."""


class LLMResponseError(HintServiceError):
    """The LLM returned an unusable response (HTTP error, bad JSON, schema mismatch)."""


logger = logging.getLogger(__name__)

# REVIEW: verify this model id exists; plagiarism_service uses "gpt-4o-mini" — consider one shared model constant.
MODEL_NAME = "gpt-5.4-mini"
REASONING = "medium"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
REQUEST_TIMEOUT = 60.0

# I have done a rudimentary test and I suspect this is redundant if you just add model_config = ConfigDict(extra="forbid")
def _make_strict_schema(schema):  # REVIEW: add type hints + docstring; non-obvious that OpenAI strict mode needs additionalProperties=false everywhere.
    schema = dict(schema)
    if schema.get("type") == "object":
        schema["additionalProperties"] = False
        if "properties" in schema:
            schema["required"] = list(schema["properties"].keys())
            schema["properties"] = {
                k: _make_strict_schema(v)
                for k, v in schema["properties"].items()
            }
    if "$defs" in schema:
        schema["$defs"] = {
            k: _make_strict_schema(v)
            for k, v in schema["$defs"].items()
        }
    if "items" in schema:
        schema["items"] = _make_strict_schema(schema["items"])
    return schema

async def _call_openai(api_key: str, user_content: str) -> HintResponse:
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        data = {
            "model": MODEL_NAME,
            "reasoning_effort": REASONING, # Give it some reasoning
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "ResponseFormat",
                    "strict": True,
                    "schema": _make_strict_schema(HintResponse.model_json_schema())  # SWAP: -> HintResponse.model_json_schema() once extra="forbid" is set on both models
                }
            }
        }
        api_response = await client.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=data)
    if api_response.status_code != 200:
        logger.error(
            "OpenAI returned HTTP %s: %s", api_response.status_code, api_response.text[:500]
        )
        raise LLMResponseError(f"OpenAI return HTTP {api_response.status_code}")  # REVIEW: typo "return" -> "returned".
    try:
        content = api_response.json()["choices"][0]["message"]["content"]
        response = HintResponse.model_validate_json(content)
        return response
    except (KeyError, IndexError, TypeError, ValidationError) as e:
        raise LLMResponseError(f"Malformed OpenAI response envelope: {e}") from e


#this could be a method of Hint()
    # def quoted_line_is_correct(self, code: str) -> bool:
    #     """True if quoted_line matches the claimed line in `code`."""
    #     lines = code.split("\n")
    #     return self.quoted_line.strip() == lines[self.line_number - 1].strip()

def _validate_hints(code: str, result: HintResponse) -> list[Hint]:
    """Keep only hints that are flagged as bugs and quote real code."""
    verified_results: list[Hint] = []
    for hint in result.hints:
        if not hint.bug:
            logger.debug(f"Skipping {hint} as its not a bug")
            continue
        if hint.quoted_line not in code: 
            logger.debug(f"Skipping {hint} as it isn't in the code")
            continue
        lines = code.split('\n')  # REVIEW: move out of the loop — recomputed every iteration.
        claimed_line = lines[hint.line_number - 1] if hint.line_number <= len(lines) else ""
        if hint.quoted_line.strip() != claimed_line.strip():
            logger.debug(f"Skipping {hint}: quoted_line doesn't match line {hint.line_number}")
            continue
        verified_results.append(hint)
    return verified_results

async def provide_hints(session: Session, code: str, validation_result: dict, game_name: Optional[str] = None, team_name: Optional[str] = None, include_game_code: bool = True) -> list[Hint]:
    context = build_hint_context_from_response(code, validation_result, game_name, team_name, include_game_code)
    api_key = get_stored_key(session, "openai")
    if not api_key:
        raise NoApiKeyError("OpenAI API key is not configured")
    raw_hints = await _call_openai(api_key, context)
    logger.debug(f"Raw hints {raw_hints}")
    return _validate_hints(code, raw_hints)
