import logging
import os
from typing import Optional

from sqlmodel import Session

from backend.database.db_models import Team
from backend.routes.ai.ai_db import get_team_attempts_ordered
from backend.routes.ai.ai_models import Hint, HintResponse
from backend.routes.ai.clients import (  # noqa: F401 — errors re-exported for callers
    LLMResponseError,
    NoApiKeyError,
    complete_structured_failover,
)
from backend.routes.ai.hint_context import build_hint_context_from_response
from backend.routes.ai.hint_prompt import SYSTEM_PROMPT
from backend.time_utils import ensure_utc, utc_now

logger = logging.getLogger(__name__)

# Ordered failover chain: try the first (provider, model); on any client error
# (missing key, HTTP error, timeout, bad response) fall through to the next.
FAILOVER_CHAIN = [
    ("openai", "gpt-5.4-mini"),
    ("google", "gemini-3.5-flash"),
]
REASONING = "medium"

# Hint rationing. Overridable per-environment (dev sets generous values in .env,
# which docker compose loads into the api container; prod falls back to these).
HINT_COOLDOWN = int(os.getenv("HINT_COOLDOWN_SECONDS", str(5 * 60)))
SUBMISSIONS_BETWEEN_HINTS = int(os.getenv("SUBMISSIONS_BETWEEN_HINTS", "3"))


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
    raw_hints, provider, model = await complete_structured_failover(
        session,
        FAILOVER_CHAIN,
        system=SYSTEM_PROMPT,
        user=context,
        schema=HintResponse,
        reasoning_effort=REASONING,
    )
    logger.debug(f"Raw hints from {provider}/{model}: {raw_hints}")
    return _validate_hints(code, raw_hints)


# WARNING: This function, if it returns True, must return True again if the same code is resubmitted.
# This means that this function must be deterministic. And only depend on data from the last hint generated
def hint_available(session: Session, team: Team) -> bool:
    all_subs = get_team_attempts_ordered(session, team.id)

    if not all_subs:
        return False

    hint_submissions_idxs = [i for i in range(len(all_subs)) if all_subs[i].hint_included]

    if not hint_submissions_idxs:
        last_submission_idx = 0
    else:
        last_submission_idx = hint_submissions_idxs[-1]

    next_submission_idx = len(all_subs)

    passed_submission_count = next_submission_idx >= (last_submission_idx + SUBMISSIONS_BETWEEN_HINTS)

    current_time = utc_now()
    last_time = ensure_utc(all_subs[last_submission_idx].timestamp)
    delta = current_time - last_time

    passed_cooldown = delta.total_seconds() >= HINT_COOLDOWN

    logger.info(f"Cooldown: {passed_cooldown}, Submission Count: {passed_submission_count}")

    return passed_cooldown and passed_submission_count
