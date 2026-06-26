import datetime
from typing import Optional
from backend.database.db_models import Team
import httpx, logging

from pydantic import ValidationError
from sqlmodel import Session

from backend.routes.ai.ai_db import get_stored_key, get_team_submissions_ordered
from backend.routes.ai.hint_prompt import SYSTEM_PROMPT
from backend.routes.ai.hint_context import build_hint_context_from_response
from backend.routes.ai.ai_models import HintResponse, Hint

class HintServiceError(Exception):
    """Base error for plagiarism service failures."""


class NoApiKeyError(HintServiceError):
    """OpenAI API key is not configured in the database."""


class LLMResponseError(HintServiceError):
    """The LLM returned an unusable response (HTTP error, bad JSON, schema mismatch)."""


logger = logging.getLogger(__name__)

MODEL_NAME = "gpt-5.4-mini"
REASONING = "medium"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
REQUEST_TIMEOUT = 60.0

HINT_COOLDOWN = 5 * 60
SUBMISSIONS_BETWEEN_HINTS = 3

async def _call_openai(api_key: str, user_content: str) -> HintResponse:
    try:
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
                        "schema": HintResponse.model_json_schema()
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
    except Exception as e:
        logger.exception(f"OpenAI conection failed {repr(e)}")
        raise LLMResponseError(f"OpenAI connection failed {e}") from e
    if api_response.status_code != 200:
        logger.error(
            "OpenAI returned HTTP %s: %s", api_response.status_code, api_response.text[:500]
        )
        raise LLMResponseError(f"OpenAI return HTTP {api_response.status_code}")
    try:
        content = api_response.json()["choices"][0]["message"]["content"]
        response = HintResponse.model_validate_json(content)
        return response
    except (KeyError, IndexError, TypeError, ValidationError) as e:
        raise LLMResponseError(f"Malformed OpenAI response envelope: {e}") from e

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
        lines = code.split('\n')
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

def hint_avaliable(session: Session, team: Team) -> bool:
    all_subs = get_team_submissions_ordered(session, team.id)
    if not all_subs:
        return False

    hint_submissions_idxs = [i for i in range(len(all_subs)) if all_subs[i].hint_included]

    if not hint_submissions_idxs:
        last_submission_idx = 0
    else:
        last_submission_idx = hint_submissions_idxs[-1]

    next_submission_idx = len(all_subs)

    logging.info(f"Hint Avaliable: There have been {next_submission_idx - last_submission_idx} submissions between new submission and last hint")

    if next_submission_idx < (last_submission_idx + SUBMISSIONS_BETWEEN_HINTS):
        logging.info(f"Hint Avaliable: Hint forbidden: Submission count")
        return False

    current_time = datetime.datetime.now(tz = datetime.timezone.utc)
    last_time = all_subs[last_submission_idx].timestamp
    delta = current_time - last_time
    
    logging.info(f"Hint Avaliable: There have been {delta.total_seconds()} seconds between new submission and last hint")

    if delta.total_seconds() < HINT_COOLDOWN:
        logging.info(f"Hint Avaliable: Hint forbidden: Cooldown")
        return False

    return True
